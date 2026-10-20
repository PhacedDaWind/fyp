"""Photo API boundary checks without requiring the unavailable local MySQL."""
import os
from unittest.mock import patch

os.environ.setdefault('DB_PASSWORD', 'unused-for-photo-api-tests')

import pytest
from fastapi.testclient import TestClient
from app import app, user
from test_recognition import photo_bytes


@pytest.fixture
def client():
    # No lifespan here: recognition doesn't access MySQL, and auth is replaced
    # with a guard identity only for these isolated route checks.
    app.dependency_overrides[user] = lambda: {'email': 'guard@test.local', 'role': 'guard'}
    with patch('app.recognize_photo') as recognize:
        c = TestClient(app, headers={'X-Parking-Client': 'admin'})
        yield c, recognize
        c.close()
    app.dependency_overrides.clear()


def test_photo_endpoint_preserves_recognition_contract(client):
    c, recognize = client
    result = {'plate': None, 'candidates': [{'text': '京A12345', 'plate': None, 'confidence': .9, 'box': [1, 2, 3, 4]}],
              'model': 'hyperlpr3-test', 'runtime': 'ONNX Runtime / CPU', 'inference_ms': 123, 'needs_review': True}
    recognize.return_value = result
    response = c.post('/api/recognition/photo', files={'photo': ('plate.png', photo_bytes(), 'image/png')})
    assert response.status_code == 200
    assert response.json() == result


def test_photo_upload_checks_limits_before_inference(client):
    c, recognize = client
    assert c.post('/api/recognition/photo', files={'photo': ('a.txt', b'a', 'text/plain')}).status_code == 415
    assert c.post('/api/recognition/photo', files={'photo': ('a.png', b'a' * 8_000_001, 'image/png')}).status_code == 413
    recognize.assert_not_called()


def test_photo_requires_client_header_and_authentication(client):
    c, recognize = client
    c.headers.pop('X-Parking-Client')
    assert c.post('/api/recognition/photo', files={'photo': ('a.png', photo_bytes(), 'image/png')}).status_code == 403
    from fastapi import HTTPException
    def signed_out():
        raise HTTPException(401, 'Please sign in')
    app.dependency_overrides[user] = signed_out
    c.headers['X-Parking-Client'] = 'admin'
    assert c.post('/api/recognition/photo', files={'photo': ('a.png', photo_bytes(), 'image/png')}).status_code == 401
    recognize.assert_not_called()


@pytest.mark.parametrize('exception,status', [(ValueError('Invalid image'), 422), (RuntimeError('Models unavailable'), 503)])
def test_photo_errors_have_useful_status(client, exception, status):
    c, recognize = client
    recognize.side_effect = exception
    assert c.post('/api/recognition/photo', files={'photo': ('a.png', photo_bytes(), 'image/png')}).status_code == status
