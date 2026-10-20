"""Local operator-only recovery, executed inside the existing API container."""
import argparse
import json
import secrets

from sqlalchemy import select, update, delete
from app import engine, meta, tables, password_hash, audit


def reset(email=None):
    meta.reflect(engine)
    tables.update(meta.tables)
    users = tables['users']
    with engine.begin() as db:
        query = select(users).where(users.c.role == 'admin')
        if email:
            query = query.where(users.c.email == email.strip().lower())
        admins = db.execute(query.with_for_update()).mappings().all()
        if len(admins) != 1:
            raise RuntimeError('Specify --email for exactly one existing administrator. Available admins: '
                               + ', '.join(row['email'] for row in admins))
        account = admins[0]
        password = secrets.token_urlsafe(24)
        db.execute(update(users).where(users.c.id == account['id']).values(password_hash=password_hash(password)))
        db.execute(delete(tables['sessions']).where(tables['sessions'].c.user_id == account['id']))
        audit(db, account, 'Administrator password reset by local operator; all sessions signed out')
    return {'email': account['email'], 'password': password}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--email')
    args = parser.parse_args()
    print(json.dumps(reset(args.email)))
