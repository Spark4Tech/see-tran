import pytest
from app import create_app, db

@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test",
        # Fake OAuth keys for test init
        "OAUTH_GOOGLE_CLIENT_ID": "x",
        "OAUTH_GOOGLE_CLIENT_SECRET": "y",
        "OAUTH_MS_CLIENT_ID": "a",
        "OAUTH_MS_CLIENT_SECRET": "b",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_login_page_renders(client):
    resp = client.get('/login')
    assert resp.status_code == 200
    assert b'Continue with Google' in resp.data
    assert b'Continue with Microsoft' in resp.data

def test_protected_redirects_to_login(client):
    # Use a protected endpoint from routes (vendors create)
    resp = client.post('/api/vendors', data={})
    # Should redirect to login
    assert resp.status_code in (302, 308)
    assert '/login' in resp.headers.get('Location', '')
