from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from ...extensions import db
from ...models import Lease, LeaseStatus, Property, Tenant
from .forms import (
    LEASE_STATUS_CHOICES,
    DeletePropertyForm,
    DeleteTenantForm,
    LeaseForm,
    PropertyForm,
    TenantForm,
)

core_bp = Blueprint("core", __name__)
STATUS_LABELS = dict(LEASE_STATUS_CHOICES)


@core_bp.route("/")
@login_required
def index():
    property_count = Property.query.count()
    tenant_count = Tenant.query.count()
    lease_count = Lease.query.count()

    today = date.today().replace(day=1)

    last_month_end = today
    last_month_start = (today - timedelta(days=1)).replace(day=1)
    property_totals: dict[str, float] = {}
    last_day_prev_month = last_month_end - timedelta(days=1)
    lease_rows = (
        db.session.query(Property.id, Property.name, func.sum(Lease.rent), func.count(Lease.id))
        .join(Property, Lease.property_id == Property.id)
        .filter(Lease.start_date <= last_day_prev_month)
        .filter(or_(Lease.end_date.is_(None), Lease.end_date >= last_month_start))
        .group_by(Property.id)
        .order_by(Property.name)
        .all()
    )

    property_totals = {}
    property_counts = {}
    for property_id, name, total, count in lease_rows:
        property_totals[name] = float(total)
        property_counts[name] = int(count)

    property_labels = list(property_totals.keys()) or ["データなし"]
    property_values = [round(total / 10000, 2) for total in property_totals.values()] or [0.0]
    property_counts_values = [property_counts.get(label, 0) for label in property_labels]

    return render_template(
        "index.html",
        property_count=property_count,
        tenant_count=tenant_count,
        lease_count=lease_count,
        property_labels=property_labels,
        property_values=property_values,
        property_counts=property_counts_values,
    )


@core_bp.route("/properties", methods=["GET", "POST"])
@login_required
def properties():
    form = PropertyForm()
    delete_form = DeletePropertyForm()
    if form.validate_on_submit():
        normalized_name = form.name.data.strip()
        existing_properties = (
            Property.query.filter(func.lower(Property.name) == normalized_name.lower())
            .order_by(Property.id)
            .all()
        )

        if existing_properties:
            canonical_property = existing_properties[0]
            canonical_property.name = normalized_name
            canonical_property.address = form.address.data
            canonical_property.note = form.note.data

            duplicates = existing_properties[1:]
            for duplicate in duplicates:
                for tenant in list(duplicate.tenants):
                    tenant.property = canonical_property
                for lease in list(duplicate.leases):
                    lease.property = canonical_property
                db.session.delete(duplicate)

            db.session.commit()
            flash("物件情報を更新しました。", "success")
            return redirect(url_for("core.properties", property_id=canonical_property.id))

        new_property = Property(
            name=normalized_name,
            address=form.address.data,
            note=form.note.data,
        )
        db.session.add(new_property)
        db.session.commit()
        flash("物件を登録しました。", "success")
        return redirect(url_for("core.properties", property_id=new_property.id))

    if delete_form.validate_on_submit():
        try:
            property_id = int(delete_form.property_id.data)
        except (TypeError, ValueError):
            flash("削除対象の情報が正しくありません。", "danger")
            return redirect(url_for("core.properties"))
        property_obj = Property.query.get_or_404(property_id)
        db.session.delete(property_obj)
        db.session.commit()
        flash("物件と関連情報を削除しました。", "info")
        return redirect(url_for("core.properties"))

    properties_list = Property.query.order_by(Property.name).all()
    delete_forms = {}
    for property_obj in properties_list:
        instance = DeletePropertyForm()
        instance.property_id.data = property_obj.id
        delete_forms[property_obj.id] = instance
    return render_template(
        "core/properties_list.html",
        properties=properties_list,
        form=form,
        delete_forms=delete_forms,
    )


@core_bp.route("/tenants", methods=["GET", "POST"])
@login_required
def tenants():
    form = TenantForm()
    properties = Property.query.order_by(Property.name).all()
    property_choices = [(prop.id, prop.name) for prop in properties]
    form.property_id.choices = property_choices
    if not properties:
        flash("先に物件を登録してください。", "warning")

    property_ids = [choice[0] for choice in property_choices]
    selected_property_id = form.property_id.data if form.property_id.data in property_ids else None
    if selected_property_id is None:
        selected_property_id = request.args.get("property_id", type=int)
        if property_ids:
            if selected_property_id not in property_ids:
                selected_property_id = property_ids[0]
        else:
            selected_property_id = None

    if form.validate_on_submit():
        new_tenant = Tenant(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            property_id=form.property_id.data,
            unit_number=form.unit_number.data,
        )
        db.session.add(new_tenant)
        db.session.commit()
        flash("入居者を登録しました。", "success")
        return redirect(url_for("core.tenants", property_id=form.property_id.data))

    if request.method == "GET" and selected_property_id is not None:
        form.property_id.data = selected_property_id

    tenants_query = Tenant.query.options(joinedload(Tenant.property)).order_by(Tenant.name)
    if selected_property_id is not None:
        tenants_query = tenants_query.filter(Tenant.property_id == selected_property_id)
    tenants_list = tenants_query.all()
    return render_template(
        "core/tenants_list.html",
        tenants=tenants_list,
        form=form,
        selected_property_id=selected_property_id,
    )


@core_bp.route("/leases", methods=["GET", "POST"])
@login_required
def leases():
    form = LeaseForm()
    properties = Property.query.order_by(Property.name).all()
    tenants = Tenant.query.order_by(Tenant.name).all()
    properties_choices = [(prop.id, prop.name) for prop in properties]
    form.property_id.choices = properties_choices

    if request.method == "GET":
        if not form.start_date.data:
            form.start_date.data = date.today()
        if not form.status.data:
            form.status.data = LeaseStatus.PENDING

    property_ids = [choice[0] for choice in properties_choices]

    selected_property_id = form.property_id.data if form.property_id.data in property_ids else None

    edit_request_id = request.args.get("lease_id", type=int)
    editing_lease = None
    if edit_request_id:
        editing_lease = (
            Lease.query.options(joinedload(Lease.property), joinedload(Lease.tenant)).filter_by(id=edit_request_id).first()
        )
        if editing_lease:
            selected_property_id = editing_lease.property_id

    if selected_property_id is None:
        selected_property_id = request.args.get("property_id", type=int)
        if property_ids:
            if selected_property_id not in property_ids:
                selected_property_id = property_ids[0]
        else:
            selected_property_id = None

    if selected_property_id is not None:
        form.property_id.data = selected_property_id

    tenants_by_property: dict[int, list[Tenant]] = {}
    for tenant in tenants:
        if tenant.property_id is None or not tenant.unit_number:
            continue
        tenants_by_property.setdefault(tenant.property_id, []).append(tenant)

    def build_unit_choices(property_id: int | None) -> list[tuple[str, str]]:
        base_choice = [("", "号室を選択")]
        if property_id is None:
            return base_choice
        units = sorted({tenant.unit_number for tenant in tenants_by_property.get(property_id, []) if tenant.unit_number})
        return base_choice + [(unit, unit) for unit in units]

    unit_choices = build_unit_choices(selected_property_id)
    form.unit_number.choices = unit_choices
    valid_units = {choice[0] for choice in unit_choices}
    if form.unit_number.data not in valid_units:
        form.unit_number.data = ""

    if editing_lease:
        if editing_lease.unit_number and editing_lease.unit_number not in valid_units:
            form.unit_number.choices.append((editing_lease.unit_number, editing_lease.unit_number))
            valid_units.add(editing_lease.unit_number)
        form.lease_id.data = str(editing_lease.id)
        form.property_id.data = editing_lease.property_id
        form.unit_number.data = editing_lease.unit_number or ""
        form.tenant_id.data = str(editing_lease.tenant_id)
        form.tenant_display.data = editing_lease.tenant.name if editing_lease.tenant else ""
        form.rent.data = float(editing_lease.rent or 0) / 10000
        form.start_date.data = editing_lease.start_date
        form.end_date.data = editing_lease.end_date
        form.status.data = editing_lease.status
        form.submit.label.text = "契約を更新"
    else:
        form.submit.label.text = "契約を保存"
        form.lease_id.data = ""

    if request.method == "POST" and (not properties_choices or not tenants):
        flash("契約を作成する前に物件と入居者を登録してください。", "warning")
        return redirect(url_for("core.leases"))

    if form.validate_on_submit():
        try:
            tenant_id = int(form.tenant_id.data)
        except (TypeError, ValueError):
            flash("有効な入居者を選択してください。", "danger")
            return redirect(url_for("core.leases"))
        property_id = form.property_id.data
        unit_number = form.unit_number.data or None
        lease_id_value = (form.lease_id.data or "").strip()
        rent_value = Decimal(str(form.rent.data or 0)) * Decimal("10000")

        if lease_id_value:
            lease = Lease.query.get(int(lease_id_value))
            if lease is None:
                flash("対象の契約が見つかりません。", "danger")
                return redirect(url_for("core.leases"))
            lease.property_id = property_id
            lease.unit_number = unit_number
            lease.tenant_id = tenant_id
            lease.rent = rent_value
            lease.start_date = form.start_date.data
            lease.end_date = form.end_date.data
            lease.status = form.status.data
            db.session.commit()
            flash("契約情報を更新しました。", "success")
            return redirect(url_for("core.leases", property_id=property_id))

        existing_lease = None
        if unit_number is not None:
            existing_lease = Lease.query.filter_by(
                property_id=property_id,
                unit_number=unit_number,
            ).first()

        if existing_lease:
            existing_lease.tenant_id = tenant_id
            existing_lease.rent = rent_value
            existing_lease.start_date = form.start_date.data
            existing_lease.end_date = form.end_date.data
            existing_lease.status = form.status.data
            db.session.commit()
            flash("契約情報を更新しました。", "success")
        else:
            new_lease = Lease(
                property_id=property_id,
                tenant_id=tenant_id,
                rent=rent_value,
                unit_number=unit_number,
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                status=form.status.data,
            )
            db.session.add(new_lease)
            db.session.commit()
            flash("契約を登録しました。", "success")
        return redirect(url_for("core.leases", property_id=property_id))

    leases_list = Lease.query.options(
        joinedload(Lease.property),
        joinedload(Lease.tenant),
    ).order_by(Lease.start_date.desc()).all()

    if selected_property_id is not None:
        leases_list = [lease for lease in leases_list if lease.property_id == selected_property_id]

    tenants_data: dict[str, list[dict[str, str]]] = {}
    for tenant in tenants:
        key = str(tenant.property_id) if tenant.property_id is not None else "0"
        tenants_data.setdefault(key, []).append(
            {
                "id": tenant.id,
                "name": tenant.name,
                "unit": tenant.unit_number or "",
            },
        )

    delete_forms = {}
    for tenant in tenants:
        instance = DeleteTenantForm()
        instance.tenant_id.data = tenant.id
        delete_forms[tenant.id] = instance

    return render_template(
        "core/leases_list.html",
        leases=leases_list,
        form=form,
        delete_forms=delete_forms,
        tenants_data=tenants_data,
        status_labels=STATUS_LABELS,
        selected_property_id=selected_property_id,
        editing_lease=editing_lease,
    )


@core_bp.route("/leases/<int:tenant_id>/delete", methods=["POST"])
@login_required
def delete_tenant(tenant_id: int):
    form = DeleteTenantForm()
    if not (form.submit.data and form.validate()):
        flash("削除に失敗しました。", "danger")
        return redirect(url_for("core.leases"))
    if int(form.tenant_id.data) != tenant_id:
        flash("削除対象の情報が一致しません。", "danger")
        return redirect(url_for("core.leases"))
    tenant = Tenant.query.get_or_404(tenant_id)
    db.session.delete(tenant)
    db.session.commit()
    flash("入居者と関連契約を削除しました。", "info")
    return redirect(url_for("core.leases"))
