from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required
from sqlalchemy.orm import joinedload

from ...extensions import db
from ...models import Lease, Property, Tenant
from .forms import DeleteForm, LeaseForm, PropertyForm, TenantForm

core_bp = Blueprint("core", __name__)


@core_bp.route("/")
@login_required
def index():
    property_count = Property.query.count()
    tenant_count = Tenant.query.count()
    lease_count = Lease.query.count()
    return render_template(
        "index.html",
        property_count=property_count,
        tenant_count=tenant_count,
        lease_count=lease_count,
    )


@core_bp.route("/properties", methods=["GET", "POST"])
@login_required
def properties():
    form = PropertyForm()
    if form.validate_on_submit():
        property_obj = Property(
            name=form.name.data.strip(),
            address=form.address.data.strip(),
            note=form.note.data,
        )
        db.session.add(property_obj)
        db.session.commit()
        flash("物件を登録しました。", "success")
        return redirect(url_for("core.properties"))

    properties_list = Property.query.order_by(Property.name.asc()).all()
    delete_forms = {prop.id: DeleteForm(id=prop.id) for prop in properties_list}

    return render_template(
        "core/properties_list.html",
        form=form,
        properties=properties_list,
        delete_forms=delete_forms,
    )


@core_bp.post("/properties/<int:property_id>/delete")
@login_required
def delete_property(property_id: int):
    form = DeleteForm()
    if not form.validate_on_submit() or int(form.id.data) != property_id:
        flash("削除に失敗しました。", "danger")
        return redirect(url_for("core.properties"))
    property_obj = Property.query.get_or_404(property_id)
    db.session.delete(property_obj)
    db.session.commit()
    flash("物件を削除しました。", "info")
    return redirect(url_for("core.properties"))


@core_bp.route("/tenants", methods=["GET", "POST"])
@login_required
def tenants():
    form = TenantForm()
    if form.validate_on_submit():
        tenant = Tenant(
            name=form.name.data.strip(),
            email=form.email.data.lower(),
            phone=form.phone.data,
        )
        db.session.add(tenant)
        db.session.commit()
        flash("入居者を登録しました。", "success")
        return redirect(url_for("core.tenants"))

    tenants_list = Tenant.query.order_by(Tenant.name.asc()).all()
    delete_forms = {tenant.id: DeleteForm(id=tenant.id) for tenant in tenants_list}

    return render_template(
        "core/tenants_list.html",
        form=form,
        tenants=tenants_list,
        delete_forms=delete_forms,
    )


@core_bp.post("/tenants/<int:tenant_id>/delete")
@login_required
def delete_tenant(tenant_id: int):
    form = DeleteForm()
    if not form.validate_on_submit() or int(form.id.data) != tenant_id:
        flash("削除に失敗しました。", "danger")
        return redirect(url_for("core.tenants"))
    tenant = Tenant.query.get_or_404(tenant_id)
    db.session.delete(tenant)
    db.session.commit()
    flash("入居者を削除しました。", "info")
    return redirect(url_for("core.tenants"))


@core_bp.route("/leases", methods=["GET", "POST"])
@login_required
def leases():
    form = LeaseForm()
    properties = Property.query.order_by(Property.name.asc()).all()
    tenants = Tenant.query.order_by(Tenant.name.asc()).all()
    form.property_id.choices = [(prop.id, prop.name) for prop in properties]
    form.tenant_id.choices = [(tenant.id, tenant.name) for tenant in tenants]

    if not properties or not tenants:
        flash("契約を作成するには物件と入居者を登録してください。", "warning")

    if form.validate_on_submit():
        lease = Lease(
            property_id=form.property_id.data,
            tenant_id=form.tenant_id.data,
            rent=form.rent.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            status=form.status.data,
        )
        db.session.add(lease)
        db.session.commit()
        flash("契約を登録しました。", "success")
        return redirect(url_for("core.leases"))

    leases_list = (
        Lease.query.options(
            joinedload(Lease.property),
            joinedload(Lease.tenant),
        )
        .order_by(Lease.start_date.desc())
        .all()
    )
    delete_forms = {lease.id: DeleteForm(id=lease.id) for lease in leases_list}

    return render_template(
        "core/leases_list.html",
        form=form,
        leases=leases_list,
        delete_forms=delete_forms,
    )


@core_bp.post("/leases/<int:lease_id>/delete")
@login_required
def delete_lease(lease_id: int):
    form = DeleteForm()
    if not form.validate_on_submit() or int(form.id.data) != lease_id:
        flash("削除に失敗しました。", "danger")
        return redirect(url_for("core.leases"))
    lease = Lease.query.get_or_404(lease_id)
    db.session.delete(lease)
    db.session.commit()
    flash("契約を削除しました。", "info")
    return redirect(url_for("core.leases"))
