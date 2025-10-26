from decimal import Decimal

import pytest

from app import create_app
from app.extensions import db
from app.models import Lease, Property, Tenant, User
from config import TestConfig


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        user = User(email="tester@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(app, client):
    response = client.post(
        "/auth/login",
        data={"email": "tester@example.com", "password": "password123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    return client


def test_index_requires_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_dashboard_authenticated(auth_client):
    response = auth_client.get("/")
    assert response.status_code == 200
    assert "ダッシュボード" in response.get_data(as_text=True)


def test_property_tenant_lease_flow(app, auth_client):
    create_property = auth_client.post(
        "/properties",
        data={"name": "HQ", "address": "1 Main St", "note": "HQ property"},
        follow_redirects=True,
    )
    assert "物件を登録しました。" in create_property.get_data(as_text=True)

    create_tenant = auth_client.post(
        "/tenants",
        data={"name": "John Doe", "email": "john@example.com", "phone": "000"},
        follow_redirects=True,
    )
    assert "入居者を登録しました。" in create_tenant.get_data(as_text=True)

    with app.app_context():
        property_id = Property.query.first().id
        tenant_id = Tenant.query.first().id

    create_lease = auth_client.post(
        "/leases",
        data={
            "property_id": str(property_id),
            "tenant_id": str(tenant_id),
            "rent": "120000.00",
            "start_date": "2024-01-01",
            "end_date": "",
            "status": "active",
        },
        follow_redirects=True,
    )
    assert "契約を登録しました。" in create_lease.get_data(as_text=True)

    with app.app_context():
        lease = Lease.query.first()
        assert lease is not None
        assert lease.property_id == property_id
        assert lease.tenant_id == tenant_id
        assert lease.rent == Decimal("120000.00")
        assert lease.status == "active"


def test_delete_tenant_removes_leases(app, auth_client):
    auth_client.post(
        "/properties",
        data={"name": "HQ", "address": "1 Main St", "note": ""},
        follow_redirects=True,
    )
    auth_client.post(
        "/tenants",
        data={"name": "Jane Doe", "email": "jane@example.com", "phone": ""},
        follow_redirects=True,
    )
    with app.app_context():
        property_id = Property.query.first().id
        tenant_id = Tenant.query.first().id
    auth_client.post(
        "/leases",
        data={
            "property_id": str(property_id),
            "tenant_id": str(tenant_id),
            "rent": "90000.00",
            "start_date": "2024-02-01",
            "end_date": "",
            "status": "active",
        },
        follow_redirects=True,
    )
    delete_tenant = auth_client.post(
        f"/tenants/{tenant_id}/delete",
        data={"id": str(tenant_id)},
        follow_redirects=True,
    )
    assert "入居者を削除しました。" in delete_tenant.get_data(as_text=True)
    with app.app_context():
        assert Tenant.query.count() == 0
        assert Lease.query.count() == 0


def test_delete_lease(app, auth_client):
    auth_client.post(
        "/properties",
        data={"name": "HQ", "address": "1 Main St", "note": ""},
        follow_redirects=True,
    )
    auth_client.post(
        "/tenants",
        data={"name": "Lease Target", "email": "target@example.com", "phone": ""},
        follow_redirects=True,
    )
    with app.app_context():
        property_id = Property.query.first().id
        tenant_id = Tenant.query.first().id
    auth_client.post(
        "/leases",
        data={
            "property_id": str(property_id),
            "tenant_id": str(tenant_id),
            "rent": "80000.00",
            "start_date": "2024-03-01",
            "end_date": "2024-12-31",
            "status": "ended",
        },
        follow_redirects=True,
    )
    with app.app_context():
        lease_id = Lease.query.first().id
    delete_lease = auth_client.post(
        f"/leases/{lease_id}/delete",
        data={"id": str(lease_id)},
        follow_redirects=True,
    )
    assert "契約を削除しました。" in delete_lease.get_data(as_text=True)
    with app.app_context():
        assert Lease.query.count() == 0


def test_delete_property_removes_leases(app, auth_client):
    auth_client.post(
        "/properties",
        data={"name": "HQ", "address": "1 Main St", "note": ""},
        follow_redirects=True,
    )
    auth_client.post(
        "/tenants",
        data={"name": "Linked Tenant", "email": "linked@example.com", "phone": ""},
        follow_redirects=True,
    )
    with app.app_context():
        property_id = Property.query.first().id
        tenant_id = Tenant.query.first().id
    auth_client.post(
        "/leases",
        data={
            "property_id": str(property_id),
            "tenant_id": str(tenant_id),
            "rent": "70000.00",
            "start_date": "2024-04-01",
            "end_date": "",
            "status": "active",
        },
        follow_redirects=True,
    )
    delete_property = auth_client.post(
        f"/properties/{property_id}/delete",
        data={"id": str(property_id)},
        follow_redirects=True,
    )
    assert "物件を削除しました。" in delete_property.get_data(as_text=True)
    with app.app_context():
        assert Property.query.count() == 0
        assert Lease.query.count() == 0
