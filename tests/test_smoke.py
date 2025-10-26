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


def test_create_property_tenant_and_lease(app, auth_client):
    property_resp = auth_client.post(
        "/properties",
        data={"name": "HQ", "address": "1 Main St", "note": "HQ property"},
        follow_redirects=True,
    )
    assert "物件を登録しました。" in property_resp.get_data(as_text=True)

    with app.app_context():
        property_id = Property.query.first().id
    tenant_resp = auth_client.post(
        "/tenants",
        data={
            "property_id": property_id,
            "unit_number": "101",
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "000",
        },
        follow_redirects=True,
    )
    assert "入居者を登録しました。" in tenant_resp.get_data(as_text=True)

    with app.app_context():
        tenant_id = Tenant.query.first().id

    lease_resp = auth_client.post(
        "/leases",
        data={
            "property_id": property_id,
            "tenant_id": tenant_id,
            "rent": "12.3",
            "unit_number": "101",
            "start_date": "2024-01-01",
            "end_date": "",
            "status": "active",
        },
        follow_redirects=True,
    )
    assert "契約を登録しました。" in lease_resp.get_data(as_text=True)

    with app.app_context():
        lease = Lease.query.first()
        assert lease is not None
        assert lease.property_id == property_id
        assert lease.tenant_id == tenant_id
        assert lease.rent == Decimal("123000")
        assert lease.unit_number == "101"

    second_tenant_resp = auth_client.post(
        "/tenants",
        data={
            "property_id": property_id,
            "unit_number": "101",
            "name": "Alice Smith",
            "email": "alice@example.com",
            "phone": "111",
        },
        follow_redirects=True,
    )
    assert "入居者を登録しました。" in second_tenant_resp.get_data(as_text=True)

    with app.app_context():
        tenant_ids = [tenant.id for tenant in Tenant.query.order_by(Tenant.id).all()]
        second_tenant_id = tenant_ids[-1]
        current_lease_id = Lease.query.first().id

    update_resp = auth_client.post(
        "/leases",
        data={
            "lease_id": str(current_lease_id),
            "property_id": property_id,
            "tenant_id": second_tenant_id,
            "rent": "15.0",
            "unit_number": "101",
            "start_date": "2024-03-01",
            "end_date": "2024-12-31",
            "status": "terminated",
        },
        follow_redirects=True,
    )
    assert "契約情報を更新しました。" in update_resp.get_data(as_text=True)

    with app.app_context():
        leases = Lease.query.all()
        assert len(leases) == 1
        updated_lease = leases[0]
        assert updated_lease.tenant_id == second_tenant_id
        assert updated_lease.rent == Decimal("150000")
        assert updated_lease.status == "terminated"
        assert str(updated_lease.end_date) == "2024-12-31"


def test_delete_tenant_removes_related_data(app, auth_client):
    property_resp = auth_client.post(
        "/properties",
        data={"name": "HQ", "address": "1 Main St", "note": "HQ property"},
        follow_redirects=True,
    )
    assert "物件を登録しました。" in property_resp.get_data(as_text=True)

    with app.app_context():
        property_id = Property.query.first().id

    tenant_resp = auth_client.post(
        "/tenants",
        data={
            "property_id": property_id,
            "unit_number": "101",
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "",
        },
        follow_redirects=True,
    )
    assert "入居者を登録しました。" in tenant_resp.get_data(as_text=True)

    with app.app_context():
        tenant_id = Tenant.query.first().id

    lease_resp = auth_client.post(
        "/leases",
        data={
            "property_id": property_id,
            "tenant_id": tenant_id,
            "rent": "9.9",
            "unit_number": "101",
            "start_date": "2024-02-01",
            "end_date": "",
            "status": "pending",
        },
        follow_redirects=True,
    )
    assert "契約を登録しました。" in lease_resp.get_data(as_text=True)

    delete_resp = auth_client.post(
        f"/leases/{tenant_id}/delete",
        data={"tenant_id": tenant_id, "submit": "削除"},
        follow_redirects=True,
    )
    assert "入居者と関連契約を削除しました。" in delete_resp.get_data(as_text=True)

    with app.app_context():
        assert Tenant.query.count() == 0
        assert Lease.query.count() == 0


def test_delete_property_removes_related_information(app, auth_client):
    property_resp = auth_client.post(
        "/properties",
        data={"name": "HQ", "address": "1 Main St", "note": "HQ property"},
        follow_redirects=True,
    )
    assert "物件を登録しました。" in property_resp.get_data(as_text=True)

    with app.app_context():
        property_id = Property.query.first().id

    tenant_resp = auth_client.post(
        "/tenants",
        data={
            "property_id": property_id,
            "unit_number": "201",
            "name": "Property Tenant",
            "email": "property_tenant@example.com",
            "phone": "999",
        },
        follow_redirects=True,
    )
    assert "入居者を登録しました。" in tenant_resp.get_data(as_text=True)

    with app.app_context():
        tenant_id = Tenant.query.first().id

    lease_resp = auth_client.post(
        "/leases",
        data={
            "property_id": property_id,
            "tenant_id": tenant_id,
            "rent": "8.0",
            "unit_number": "201",
            "start_date": "2024-04-01",
            "end_date": "",
            "status": "active",
        },
        follow_redirects=True,
    )
    assert "契約を登録しました。" in lease_resp.get_data(as_text=True)

    delete_resp = auth_client.post(
        "/properties",
        data={"property_id": property_id, "submit": "削除"},
        follow_redirects=True,
    )
    assert "物件と関連情報を削除しました。" in delete_resp.get_data(as_text=True)

    with app.app_context():
        assert Property.query.count() == 0
        assert Tenant.query.count() == 0
        assert Lease.query.count() == 0


def test_property_creation_overwrites_existing(app, auth_client):
    create_resp = auth_client.post(
        "/properties",
        data={"name": "HQ", "address": "1 Main St", "note": "Original"},
        follow_redirects=True,
    )
    assert "物件を登録しました。" in create_resp.get_data(as_text=True)

    with app.app_context():
        property_id = Property.query.first().id

    tenant_resp = auth_client.post(
        "/tenants",
        data={
            "property_id": property_id,
            "unit_number": "301",
            "name": "Overwrite Tenant",
            "email": "overwrite@example.com",
            "phone": "555",
        },
        follow_redirects=True,
    )
    assert "入居者を登録しました。" in tenant_resp.get_data(as_text=True)

    update_resp = auth_client.post(
        "/properties",
        data={"name": "HQ", "address": "2 Main St", "note": "Updated"},
        follow_redirects=True,
    )
    assert "物件情報を更新しました。" in update_resp.get_data(as_text=True)

    with app.app_context():
        properties = Property.query.all()
        assert len(properties) == 1
        property_obj = properties[0]
        assert property_obj.address == "2 Main St"
        assert property_obj.note == "Updated"
        tenant = Tenant.query.first()
        assert tenant is not None
        assert tenant.property_id == property_obj.id
