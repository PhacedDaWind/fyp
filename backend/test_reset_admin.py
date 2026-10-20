import os
os.environ.setdefault('DB_PASSWORD', 'unused-for-recovery-tests')

import pytest
from sqlalchemy import create_engine, MetaData, Table, Column, String, BigInteger, insert, select
import reset_admin
from app import check_password


@pytest.fixture
def database(monkeypatch):
    engine = create_engine('sqlite://')
    meta = MetaData()
    Table('users', meta, Column('id', String, primary_key=True), Column('email', String), Column('role', String), Column('password_hash', String))
    Table('sessions', meta, Column('token', String, primary_key=True), Column('user_id', String), Column('expires', BigInteger))
    Table('activity', meta, Column('id', String, primary_key=True), Column('actor', String), Column('message', String), Column('at', String))
    meta.create_all(engine)
    # reset_admin.audit references app.tables; use a local audit writer here.
    def audit(db, account, message):
        db.execute(insert(meta.tables['activity']).values(id='audit1', actor=account['email'], message=message, at='now'))
    monkeypatch.setattr(reset_admin, 'engine', engine)
    monkeypatch.setattr(reset_admin, 'meta', meta)
    monkeypatch.setattr(reset_admin, 'tables', {})
    monkeypatch.setattr(reset_admin, 'audit', audit)
    with engine.begin() as db:
        db.execute(insert(meta.tables['users']), [dict(id='admin', email='admin@test.local', role='admin', password_hash='old'), dict(id='guard', email='guard@test.local', role='guard', password_hash='untouched')])
        db.execute(insert(meta.tables['sessions']), [dict(token='a',user_id='admin',expires=9999999999),dict(token='g',user_id='guard',expires=9999999999)])
    yield engine, meta
    engine.dispose()


def test_recovery_resets_only_selected_admin_and_revokes_their_sessions(database):
    engine, meta = database
    result = reset_admin.reset('admin@test.local')
    with engine.connect() as db:
        users = {row['id']: row for row in db.execute(select(meta.tables['users'])).mappings()}
        assert check_password(result['password'], users['admin']['password_hash'])
        assert users['guard']['password_hash'] == 'untouched'
        assert db.execute(select(meta.tables['sessions'].c.token)).scalars().all() == ['g']
        assert db.execute(select(meta.tables['activity'].c.actor)).scalar_one() == 'admin@test.local'


def test_recovery_cannot_reset_a_guard_or_unknown_account(database):
    with pytest.raises(RuntimeError, match='existing administrator'):
        reset_admin.reset('guard@test.local')


def test_recovery_requires_selection_when_multiple_admins_exist(database):
    engine, meta = database
    with engine.begin() as db:
        db.execute(insert(meta.tables['users']).values(id='other',email='other@test.local',role='admin',password_hash='old'))
    with pytest.raises(RuntimeError, match='--email'):
        reset_admin.reset()
