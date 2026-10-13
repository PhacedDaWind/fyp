import time
import secrets
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert, delete, update, select
from app import app, engine, tables, uid, password_hash

@pytest.fixture
def client():
    prefix='T'+secrets.token_hex(3).upper()
    email=prefix.lower()+'@test.local'
    password=secrets.token_urlsafe(20)
    with TestClient(app) as c:
        with engine.begin() as db:
            db.execute(insert(tables['users']).values(id=uid(),email=email,password_hash=password_hash(password),role='admin'))
        c.headers['X-Parking-Client']='admin'
        assert c.post('/api/login',json={'email':email,'password':password}).status_code==200
        c.prefix=prefix;c.email=email;c.password=password
        yield c
        with engine.begin() as db:
            for name in ['visits','attempts','vehicles']:
                db.execute(delete(tables[name]).where(tables[name].c.plate.like(prefix+'%')))
            db.execute(delete(tables['activity']).where(tables['activity'].c.actor.like(prefix.lower()+'%')))
            users=select(tables['users'].c.id).where(tables['users'].c.email.like(prefix.lower()+'%'))
            db.execute(delete(tables['sessions']).where(tables['sessions'].c.user_id.in_(users)))
            db.execute(delete(tables['users']).where(tables['users'].c.email.like(prefix.lower()+'%')))

def vehicle(c, **kw):
    return dict(plate=c.prefix+'1',owner='Test Driver',ownerId='TEST1',category='Student',model='',notes='',validFrom='2020-01-01',validTo='2099-12-31',blocked=False,**kw)
def scan(c,direction='entry',suffix='1'):
    r=c.post('/api/simulator/scan',json={'id':uid(),'plate':c.prefix+suffix,'direction':direction})
    assert r.status_code==200,r.text
    return r.json()
def confirm(c,a):return c.post('/api/simulator/'+a['id']+'/passage')
def visits(c):return [v for v in c.get('/api/visits').json() if v['plate'].startswith(c.prefix)]

def test_requires_auth_and_csrf(client):
    assert client.post('/api/logout').status_code==200
    assert client.get('/api/state').status_code==401
    client.headers.pop('X-Parking-Client')
    assert client.post('/api/login',json={'email':client.email,'password':client.password}).status_code==403

def test_password_change_validates_and_revokes_sessions(client):
    payload={'current_password':client.password,'new_password':'New-test-password-123','confirm_password':'New-test-password-123'}
    assert client.post('/api/password',json={**payload,'current_password':'wrong'}).status_code==400
    assert client.post('/api/password',json={**payload,'confirm_password':'not-matching-password'}).status_code==422
    assert client.post('/api/password',json={**payload,'new_password':'short'}).status_code==422
    with TestClient(app) as other:
        other.headers['X-Parking-Client']='admin'
        assert other.post('/api/login',json={'email':client.email,'password':client.password}).status_code==200
        assert client.post('/api/password',json=payload).status_code==200
        assert other.get('/api/me').status_code==401
    assert client.get('/api/me').status_code==401
    assert client.post('/api/login',json={'email':client.email,'password':client.password}).status_code==401
    assert client.post('/api/login',json={'email':client.email,'password':payload['new_password']}).status_code==200

def test_batch_registration_atomic_validation(client):
    one=vehicle(client);two={**one,'plate':client.prefix+'2'}
    assert client.post('/api/vehicles/batch',json={'vehicles':[one,two]}).json()['count']==2
    third={**one,'plate':client.prefix+'3'}
    assert client.post('/api/vehicles/batch',json={'vehicles':[third,one]}).status_code==409
    assert client.post('/api/vehicles/batch',json={'vehicles':[third,{**third,'plate':third['plate'].lower()}]}).status_code==409
    assert client.post('/api/vehicles/batch',json={'vehicles':[third,{**two,'validTo':'2010-01-01'}]}).status_code==422
    records=client.get('/api/state').json()['vehicles']
    assert not any(v['plate']==third['plate'] for v in records)
    with engine.begin() as db: db.execute(update(tables['users']).where(tables['users'].c.email==client.email).values(role='guard'))
    assert client.post('/api/vehicles/batch',json={'vehicles':[third]}).status_code==403

def test_vehicle_crud_validation_and_uniqueness(client):
    v=vehicle(client);assert client.post('/api/vehicles',json=v).status_code==200
    assert client.post('/api/vehicles',json={**v,'plate':' '+v['plate'].lower()+' '}).status_code==409
    assert client.post('/api/vehicles',json={**v,'plate':client.prefix+'2','validTo':'2010-01-01'}).status_code==422
    row=next(v for v in client.get('/api/state').json()['vehicles'] if v['plate']==client.prefix+'1')
    assert client.put('/api/vehicles/'+row['id'],json={**row,'blocked':True}).status_code==200
    assert scan(client)['decision']=='DENY'
    assert client.delete('/api/vehicles/'+row['id']).status_code==200

def test_registered_entry_saved_only_after_passage(client):
    client.post('/api/vehicles',json=vehicle(client))
    a=scan(client);assert a['decision']=='ALLOW';assert visits(client)==[]
    assert confirm(client,a).status_code==200
    assert confirm(client,a).status_code==200
    assert len(visits(client))==1
    assert visits(client)[0]['status']=='INSIDE'
    assert scan(client)['decision']=='DENY'

def test_guest_requires_guard_and_not_permanent_permission(client):
    a=scan(client);assert a['decision']=='REVIEW'
    assert confirm(client,a).status_code==409
    assert client.post('/api/simulator/'+a['id']+'/open').status_code==200
    assert visits(client)==[]
    assert confirm(client,a).status_code==200
    assert visits(client)[0]['kind']=='Guest'
    assert confirm(client,scan(client,'exit')).status_code==200
    assert scan(client)['decision']=='REVIEW'

def test_exit_ignores_block_status_and_saves_duration(client):
    client.post('/api/vehicles',json=vehicle(client));confirm(client,scan(client))
    row=next(v for v in client.get('/api/state').json()['vehicles'] if v['plate']==client.prefix+'1')
    client.put('/api/vehicles/'+row['id'],json={**row,'blocked':True,'validTo':'2021-01-01'})
    a=scan(client,'exit');assert a['decision']=='ALLOW';assert a['duration_seconds']>=0
    assert visits(client)[0]['status']=='INSIDE'
    assert confirm(client,a).status_code==200
    assert confirm(client,a).status_code==200
    v=visits(client);assert len(v)==1;assert v[0]['status']=='EXITED';assert v[0]['duration_seconds']>=0

def test_exit_without_entry(client):
    a=scan(client,'exit');assert a['decision']=='ALLOW';assert a['duration_seconds'] is None
    confirm(client,a);v=visits(client)[0];assert v['status']=='EXITED';assert v['entry_at'] is None

def test_expired_attempt(client):
    a=scan(client,'exit')
    with engine.begin() as db: db.execute(update(tables['attempts']).where(tables['attempts'].c.id==a['id']).values(created=int(time.time())-301))
    assert confirm(client,a).status_code==409
    assert not visits(client)

def test_scan_id_reuse(client):
    payload={'id':uid(),'plate':client.prefix+'1','direction':'exit'}
    assert client.post('/api/simulator/scan',json=payload).status_code==200
    assert client.post('/api/simulator/scan',json=payload).status_code==200
    assert client.post('/api/simulator/scan',json={**payload,'plate':client.prefix+'2'}).status_code==409

def test_guard_cannot_manage_registry(client):
    with engine.begin() as db: db.execute(update(tables['users']).where(tables['users'].c.email==client.email).values(role='guard'))
    assert client.get('/api/state').status_code==403
    assert client.post('/api/vehicles',json=vehicle(client)).status_code==403
    assert client.post('/api/users',json={'email':'x@test.local','password':'long-test-password','role':'admin'}).status_code==403
    assert scan(client)['decision']=='REVIEW'

def test_permission_rechecked_before_entry(client):
    client.post('/api/vehicles',json=vehicle(client));a=scan(client)
    with engine.begin() as db: db.execute(update(tables['vehicles']).where(tables['vehicles'].c.plate==client.prefix+'1').values(blocked=True))
    assert confirm(client,a).status_code==409
    assert not visits(client)

def test_duplicate_distinct_exit_does_not_create_extra_visit(client):
    client.post('/api/vehicles',json=vehicle(client));confirm(client,scan(client))
    a,b=scan(client,'exit'),scan(client,'exit')
    assert confirm(client,a).status_code==200
    assert confirm(client,b).status_code==409
    assert len(visits(client))==1
