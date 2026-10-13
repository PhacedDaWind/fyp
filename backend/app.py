"""Local parking API. Recognition and gate actions are explicitly simulated."""
import hashlib
import hmac
import os
import re
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta, date
from uuid import uuid4

from fastapi import FastAPI, Depends, HTTPException, Request, Response, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, MetaData, Table, select, insert, update, delete
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError
from recognition import simulated_reading, recognize_photo

engine = create_engine(URL.create('mysql+pymysql', username='parking', password=os.environ['DB_PASSWORD'], host='db', database='parking'), pool_pre_ping=True)
meta = MetaData()
tables = {}
def uid(): return str(uuid4())
def now(): return datetime.now(timezone.utc)
def stamp(): return now().isoformat()
def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + ':' + hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
def check_password(password, encoded):
    return hmac.compare_digest(password_hash(password, encoded.split(':')[0]), encoded)
def audit(c, user, message):
    c.execute(insert(tables['activity']).values(id=uid(), actor=user['email'], message=message, at=stamp()))

@asynccontextmanager
async def lifespan(app):
    meta.reflect(engine)
    tables.update(meta.tables)
    with engine.begin() as c:
        email = os.environ.get('ADMIN_EMAIL', '').lower()
        password = os.environ.get('ADMIN_PASSWORD', '')
        if email and len(password) >= 12 and not c.execute(select(tables['users']).where(tables['users'].c.email == email)).first():
            c.execute(insert(tables['users']).values(id=uid(), email=email, password_hash=password_hash(password), role='admin'))
    yield

app = FastAPI(title='HELP Parking API', lifespan=lifespan)

@app.middleware('http')
async def csrf(request, call_next):
    # Browsers cannot send this custom header cross-origin without a preflight.
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE') and request.headers.get('X-Parking-Client') != 'admin':
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail': 'Missing client header'}, status_code=403)
    return await call_next(request)

@app.exception_handler(IntegrityError)
async def conflict(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse({'detail': 'This plate or record already exists. Refresh and try again.'}, status_code=409)

def user(request: Request):
    token = hashlib.sha256(request.cookies.get('parking_session', '').encode()).hexdigest()
    with engine.connect() as c:
        s, u = tables['sessions'], tables['users']
        row = c.execute(select(u).join(s, s.c.user_id == u.c.id).where(s.c.token == token, s.c.expires > time.time())).mappings().first()
        if not row: raise HTTPException(401, 'Please sign in')
        return dict(row)
def admin(u=Depends(user)):
    if u['role'] != 'admin': raise HTTPException(403, 'Administrator access required')
    return u
class Login(BaseModel):
    email: str = Field(max_length=150)
    password: str = Field(max_length=256)
failures = {}
@app.post('/api/login')
def login(data: Login, response: Response, request: Request):
    key = request.client.host
    recent = [t for t in failures.get(key, []) if t > time.time()-300]
    if len(recent) >= 15: raise HTTPException(429, 'Too many attempts. Wait five minutes.')
    with engine.begin() as c:
        u = c.execute(select(tables['users']).where(tables['users'].c.email == data.email.strip().lower())).mappings().first()
        valid = check_password(data.password, u['password_hash'] if u else password_hash('invalid-password'))
        if not u or not valid:
            failures[key] = recent + [time.time()]
            raise HTTPException(401, 'Incorrect email or password')
        failures.pop(key, None)
        token = secrets.token_urlsafe(32)
        c.execute(delete(tables['sessions']).where(tables['sessions'].c.expires < time.time()))
        c.execute(insert(tables['sessions']).values(token=hashlib.sha256(token.encode()).hexdigest(), user_id=u['id'], expires=int(time.time())+28800))
        response.set_cookie('parking_session', token, httponly=True, samesite='strict', max_age=28800, secure=os.getenv('COOKIE_SECURE') == 'true')
    return {'email': u['email'], 'role': u['role']}
@app.get('/api/me')
def me(u=Depends(user)): return {'email': u['email'], 'role': u['role']}
@app.post('/api/logout')
def logout(request: Request, response: Response):
    with engine.begin() as c:
        c.execute(delete(tables['sessions']).where(tables['sessions'].c.token == hashlib.sha256(request.cookies.get('parking_session','').encode()).hexdigest()))
    response.delete_cookie('parking_session')
    return {'ok': True}
class NewUser(Login):
    role: str
class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)
    confirm_password: str = Field(min_length=12, max_length=256)

@app.post('/api/password')
def change_password(data: PasswordChange, response: Response, u=Depends(user)):
    if data.new_password != data.confirm_password:
        raise HTTPException(422, 'New passwords do not match')
    if data.new_password == data.current_password:
        raise HTTPException(422, 'Choose a different new password')
    key = 'password:' + u['id']
    recent = [t for t in failures.get(key, []) if t > time.time()-300]
    if len(recent) >= 10: raise HTTPException(429, 'Too many attempts. Wait five minutes.')
    with engine.begin() as c:
        row = c.execute(select(tables['users']).where(tables['users'].c.id == u['id']).with_for_update()).mappings().one()
        if not check_password(data.current_password, row['password_hash']):
            failures[key] = recent + [time.time()]
            raise HTTPException(400, 'Current password is incorrect')
        c.execute(update(tables['users']).where(tables['users'].c.id == u['id']).values(password_hash=password_hash(data.new_password)))
        c.execute(delete(tables['sessions']).where(tables['sessions'].c.user_id == u['id']))
        audit(c, u, 'Changed account password; all sessions signed out')
    failures.pop(key, None)
    response.delete_cookie('parking_session')
    return {'ok': True}
@app.post('/api/users')
def add_user(data: NewUser, u=Depends(admin)):
    if data.role not in ('admin','guard') or len(data.password) < 12 or '@' not in data.email: raise HTTPException(422, 'Use a valid email, admin/guard role and 12+ character password')
    with engine.begin() as c:
        c.execute(insert(tables['users']).values(id=uid(), email=data.email.lower().strip(), password_hash=password_hash(data.password), role=data.role))
        audit(c,u,'Created '+data.role+' account '+data.email)
    return {'ok':True}
@app.get('/api/state')
def state(u=Depends(admin)):
    with engine.connect() as c:
        return {'vehicles':[dict(v) for v in c.execute(select(tables['vehicles'])).mappings()], 'activity':[dict(v) for v in c.execute(select(tables['activity']).order_by(tables['activity'].c.at.desc()).limit(200)).mappings()], 'demo':False}
class Vehicle(BaseModel):
    plate: str = Field(max_length=20)
    owner: str = Field(min_length=1,max_length=100)
    category: str
    ownerId: str = Field(default='',max_length=50)
    model: str = Field(default='',max_length=100)
    validFrom: date
    validTo: date
    notes: str = Field(default='',max_length=500)
    blocked: bool = False
def plate(value):
    value = re.sub(r'\s','',value).upper()
    if not re.fullmatch('[A-Z0-9]{2,12}',value): raise HTTPException(422,'Plate must contain 2–12 letters or numbers')
    return value

@app.post('/api/recognition/photo')
def read_plate_photo(photo: UploadFile = File(...), u=Depends(user)):
    if photo.content_type not in ('image/jpeg', 'image/png', 'image/webp'):
        raise HTTPException(415, 'Choose a JPEG, PNG or WebP photo')
    data = photo.file.read(8_000_001)
    if len(data) > 8_000_000:
        raise HTTPException(413, 'Photo must be smaller than 8 MB')
    try:
        reading = recognize_photo(data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return {'plate': reading.plate if reading else None,
            'model': reading.model if reading else 'tesseract-baseline',
            'confidence': None, 'needs_review': True}
def vehicle_values(data):
    if data.category not in ('Student','Staff','Visitor') or not data.owner.strip() or (data.category != 'Visitor' and not data.ownerId.strip()): raise HTTPException(422,'Invalid owner/category/reference')
    if data.validTo < data.validFrom: raise HTTPException(422,'Finish date is before start date')
    return {**data.model_dump(mode='json'), 'plate':plate(data.plate), 'owner':data.owner.strip()}
@app.post('/api/vehicles')
def create_vehicle(data: Vehicle,u=Depends(admin)):
    values=vehicle_values(data)
    with engine.begin() as c:
        c.execute(insert(tables['vehicles']).values(id=uid(),**values)); audit(c,u,values['plate']+' registered')
    return {'ok':True}
class VehicleBatch(BaseModel):
    vehicles: list[Vehicle] = Field(min_length=1, max_length=100)

@app.post('/api/vehicles/batch')
def create_vehicles(data: VehicleBatch, u=Depends(admin)):
    values = [vehicle_values(v) for v in data.vehicles]
    plates = [v['plate'] for v in values]
    if len(plates) != len(set(plates)):
        raise HTTPException(409, 'Duplicate plates in this batch. No vehicles saved.')
    with engine.begin() as c:
        existing = c.execute(select(tables['vehicles'].c.plate).where(tables['vehicles'].c.plate.in_(plates))).scalars().all()
        if existing:
            raise HTTPException(409, 'Already registered: ' + ', '.join(existing) + '. No vehicles saved.')
        c.execute(insert(tables['vehicles']), [{'id':uid(), **v} for v in values])
        for v in values: audit(c, u, v['plate'] + ' registered in batch')
    return {'ok': True, 'count': len(values)}
@app.put('/api/vehicles/{id}')
def edit_vehicle(id: str,data: Vehicle,u=Depends(admin)):
    values=vehicle_values(data)
    with engine.begin() as c:
        if not c.execute(select(tables['vehicles']).where(tables['vehicles'].c.id==id)).first(): raise HTTPException(404,'Vehicle not found')
        c.execute(update(tables['vehicles']).where(tables['vehicles'].c.id==id).values(**values)); audit(c,u,values['plate']+' updated')
    return {'ok':True}
@app.delete('/api/vehicles/{id}')
def remove_vehicle(id: str,u=Depends(admin)):
    with engine.begin() as c:
        v=c.execute(select(tables['vehicles']).where(tables['vehicles'].c.id==id)).mappings().first()
        if not v: raise HTTPException(404,'Vehicle not found')
        c.execute(delete(tables['vehicles']).where(tables['vehicles'].c.id==id));audit(c,u,v['plate']+' removed from registry; visit history retained')
    return {'ok':True}
class Scan(BaseModel):
    id: str = Field(min_length=36,max_length=36)
    plate: str = Field(max_length=20)
    direction: str
@app.post('/api/simulator/scan')
def scan(data: Scan,u=Depends(user)):
    p=plate(simulated_reading(data.plate).plate)
    if data.direction not in ('entry','exit'): raise HTTPException(422,'Choose entry or exit')
    with engine.begin() as c:
        a,v,vis=tables['attempts'],tables['vehicles'],tables['visits']
        existing=c.execute(select(a).where(a.c.id==data.id)).mappings().first()
        if existing:
            if existing['plate']!=p or existing['direction']!=data.direction: raise HTTPException(409,'Attempt ID already used')
            return dict(existing)
        record=c.execute(select(v).where(v.c.plate==p)).mappings().first()
        visit=c.execute(select(vis).where(vis.c.open_plate==p)).mappings().first()
        decision,reason='ALLOW','Exit: no status checks'
        if data.direction=='entry':
            today=(now()+timedelta(hours=8)).date().isoformat()
            if visit: decision,reason='DENY','Vehicle already has an open visit'
            elif not record: decision,reason='REVIEW','Unknown plate: guard must manually open'
            elif record['blocked'] or not record['validFrom']<=today<=record['validTo']: decision,reason='DENY','Blocked or outside permit dates'
            else: reason='Valid parking permission'
        duration=max(0,int((now()-datetime.fromisoformat(visit['entry_at'])).total_seconds())) if visit and visit['entry_at'] else None
        result=dict(id=data.id,plate=p,direction=data.direction,decision=decision,reason=reason,created=int(time.time()),approved_by=None,confirmed=False,visit_id=visit['id'] if visit else None,duration_seconds=duration)
        c.execute(insert(a).values(**result));audit(c,u,f'Simulated {data.direction} scan {p}: {decision}')
        return result
@app.post('/api/simulator/{id}/open')
def manual_open(id:str,u=Depends(user)):
    with engine.begin() as c:
        a=tables['attempts'];row=c.execute(select(a).where(a.c.id==id).with_for_update()).mappings().first()
        if not row: raise HTTPException(404,'Attempt not found')
        if row['confirmed'] or row['created']<time.time()-300: raise HTTPException(409,'Attempt completed or expired; scan again')
        if row['decision']!='REVIEW': raise HTTPException(409,'Only unknown guest entry requires manual opening')
        c.execute(update(a).where(a.c.id==id).values(decision='ALLOW',approved_by=u['email'],reason='Guard manually opened simulated gate'))
        audit(c,u,'Manually opened simulated gate for '+row['plate'])
    return {'ok':True}
@app.post('/api/simulator/{id}/passage')
def passage(id:str,u=Depends(user)):
    with engine.begin() as c:
        a,vis=tables['attempts'],tables['visits']
        row=c.execute(select(a).where(a.c.id==id).with_for_update()).mappings().first()
        if not row: raise HTTPException(404,'Attempt not found')
        if row['confirmed']: return {'ok':True,'visit_id':row['visit_id']}
        if row['decision']!='ALLOW' or row['created']<time.time()-300: raise HTTPException(409,'Gate is not allowed to open or scan expired')
        current=c.execute(select(vis).where(vis.c.open_plate==row['plate']).with_for_update()).mappings().first()
        at=stamp();visit_id=uid()
        if row['direction']=='entry':
            if current: raise HTTPException(409,'Car already inside')
            # Recheck registry permission at passage to avoid using a stale allow.
            v=c.execute(select(tables['vehicles']).where(tables['vehicles'].c.plate==row['plate'])).mappings().first()
            today=(now()+timedelta(hours=8)).date().isoformat()
            if not row['approved_by'] and (not v or v['blocked'] or not v['validFrom']<=today<=v['validTo']): raise HTTPException(409,'Permission changed; scan again')
            c.execute(insert(vis).values(id=visit_id,plate=row['plate'],kind='Guest' if row['approved_by'] else 'Registered',entry_at=at,status='INSIDE',guard=row['approved_by'],entry_attempt=id,open_plate=row['plate']))
        elif current:
            # A delayed exit attempt must not close a later visit.
            if current['id']!=row['visit_id']: raise HTTPException(409,'Visit changed; scan again')
            visit_id=current['id'];seconds=max(0,int((datetime.fromisoformat(at)-datetime.fromisoformat(current['entry_at'])).total_seconds()))
            c.execute(update(vis).where(vis.c.id==visit_id).values(exit_at=at,duration_seconds=seconds,status='EXITED',exit_attempt=id,open_plate=None))
        else:
            if row['visit_id']: raise HTTPException(409,'Visit already exited; scan again')
            c.execute(insert(vis).values(id=visit_id,plate=row['plate'],kind='Unmatched',exit_at=at,status='EXITED',exit_attempt=id))
        c.execute(update(a).where(a.c.id==id).values(confirmed=True,visit_id=visit_id))
        audit(c,u,f"Confirmed {row['direction']} passage {row['plate']}")
        return {'ok':True,'visit_id':visit_id}
@app.get('/api/visits')
def visits(u=Depends(user)):
    with engine.connect() as c: return [dict(r) for r in c.execute(select(tables['visits']).order_by(tables['visits'].c.entry_at.desc(),tables['visits'].c.exit_at.desc()).limit(1000)).mappings()]
@app.get('/api/health')
def health(): return {'status':'ok','recognition':'simulated','hardware':'simulated'}
