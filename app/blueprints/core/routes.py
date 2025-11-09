"""物件・入居者・契約のダッシュボードおよび CRUD ルートを束ねる Blueprint。"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload
from urllib.parse import urlparse

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
    """ダッシュボード: 直近データの集計結果をカード+チャートで表示する。"""
    property_count = Property.query.count()
    tenant_count = Tenant.query.count()
    lease_count = Lease.query.count()

    # 先月分の稼働実績を算出するために月初・月末を固定しておく。
    today = date.today().replace(day=1)

    last_month_end = today
    last_month_start = (today - timedelta(days=1)).replace(day=1)
    property_totals: dict[str, float] = {}
    last_day_prev_month = last_month_end - timedelta(days=1)
    # 集計は SQL 側でまとめ、Python ではラベル整形のみを行う。
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

    # グラフ側で空データにならないようプレースホルダーを用意。
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
    """物件の一覧表示と新規作成/更新/重複マージ/削除を同じ画面で扱う。"""
    form = PropertyForm()
    delete_form = DeletePropertyForm()

    # GET property_id=xx があればフォームを編集モードに切り替える。
    edit_property_id = request.args.get("property_id", type=int)
    editing_property = None
    if edit_property_id is not None:
        editing_property = Property.query.get(edit_property_id)
        if editing_property:
            form.property_id.data = str(edit_property_id)
            if request.method == "GET":
                form.name.data = editing_property.name
                form.address.data = editing_property.address
                form.note.data = editing_property.note

    form.submit.label.text = "物件を更新" if editing_property else "物件を保存"

    # 「保存」系ボタンは常に PropertyForm を使うためここで処理を分岐。
    if form.validate_on_submit():
        property_id_raw = (form.property_id.data or "").strip()
        property_id_value = int(property_id_raw) if property_id_raw.isdigit() else None
        normalized_name = form.name.data.strip()
        existing_properties = (
            Property.query.filter(func.lower(Property.name) == normalized_name.lower())
            .order_by(Property.id)
            .all()
        )

        if property_id_value:
            # 既存物件を更新しつつ、重複 Name をマージする。
            property_obj = Property.query.get_or_404(property_id_value)
            property_obj.name = normalized_name
            property_obj.address = form.address.data
            property_obj.note = form.note.data

            duplicates = [prop for prop in existing_properties if prop.id != property_obj.id]
            for duplicate in duplicates:
                for tenant in list(duplicate.tenants):
                    tenant.property = property_obj
                for lease in list(duplicate.leases):
                    lease.property = property_obj
                db.session.delete(duplicate)

            db.session.commit()
            flash("物件情報を更新しました。", "success")
            return redirect(url_for("core.properties"))

        if existing_properties:
            # 新規登録でも同名物件がある場合は先勝ちの1件に集約する。
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
            return redirect(url_for("core.properties"))

        new_property = Property(
            name=normalized_name,
            address=form.address.data,
            note=form.note.data,
        )
        db.session.add(new_property)
        db.session.commit()
        flash("物件を登録しました。", "success")
        return redirect(url_for("core.properties"))

    if delete_form.validate_on_submit():
        # 削除は CSRF 付き個別フォームを使い、関連リレーションごと落とす。
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

    # 一覧テーブルを描画するためのデータと削除フォームを構築。
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
        editing_property=editing_property,
    )


@core_bp.route("/tenants", methods=["GET", "POST"])
@login_required
def tenants():
    """入居者の物件別フィルタ・一覧・編集を 1 画面で提供する。"""
    form = TenantForm()
    properties = Property.query.order_by(Property.name).all()
    property_choices = [(prop.id, prop.name) for prop in properties]
    form.property_id.choices = property_choices
    # 物件が無い場合は早期に利用者へ案内する。
    if not properties:
        flash("先に物件を登録してください。", "warning")

    property_ids = [choice[0] for choice in property_choices]
    selected_property_id = form.property_id.data if form.property_id.data in property_ids else None
    if selected_property_id is None:
        # URL クエリから選択物件を決め、なければ先頭をフォールバック。
        selected_property_id = request.args.get("property_id", type=int)
        if property_ids:
            if selected_property_id not in property_ids:
                selected_property_id = property_ids[0]
        else:
            selected_property_id = None

    edit_tenant_id = request.args.get("tenant_id", type=int)
    if edit_tenant_id is None:
        # POST 後のバリデーションで tenant_id が失われないよう hidden を参照。
        tenant_id_raw = (form.tenant_id.data or "").strip()
        if tenant_id_raw.isdigit():
            edit_tenant_id = int(tenant_id_raw)

    editing_tenant = None
    if edit_tenant_id:
        editing_tenant = Tenant.query.get(edit_tenant_id)
        if editing_tenant:
            selected_property_id = editing_tenant.property_id
            form.tenant_id.data = str(edit_tenant_id)
            if request.method == "GET":
                form.property_id.data = editing_tenant.property_id
                form.unit_number.data = editing_tenant.unit_number or ""
                form.name.data = editing_tenant.name
                form.email.data = editing_tenant.email or ""
                form.phone.data = editing_tenant.phone or ""
        else:
            form.tenant_id.data = ""

    form.submit.label.text = "入居者を更新" if editing_tenant else "入居者を保存"

    # submit 時には hidden の tenant_id 有無で新規/更新を振り分ける。
    # バリデーションで落ちた場合もここを再実行するので状態復元が必要。
    if form.validate_on_submit():
        tenant_id_value = (form.tenant_id.data or "").strip()
        if tenant_id_value:
            tenant_obj = Tenant.query.get_or_404(int(tenant_id_value))
            tenant_obj.property_id = form.property_id.data
            tenant_obj.unit_number = form.unit_number.data
            tenant_obj.name = form.name.data
            tenant_obj.email = form.email.data or ""
            tenant_obj.phone = form.phone.data or ""
            db.session.commit()
            flash("入居者情報を更新しました。", "success")
            return redirect(url_for("core.tenants", property_id=form.property_id.data))

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

    # GET 直後は property_id が未設定なので、選択している物件を改めて反映。
    if request.method == "GET" and selected_property_id is not None:
        form.property_id.data = selected_property_id

    # テーブルは property -> tenant の順で並べる。joinedload で N+1 を防ぐ。
    tenants_query = (
        Tenant.query.options(joinedload(Tenant.property))
        .outerjoin(Property)
        .order_by(Property.name.asc(), Tenant.unit_number.asc(), Tenant.name.asc())
    )
    if selected_property_id is not None:
        tenants_query = tenants_query.filter(Tenant.property_id == selected_property_id)
    tenants_list = tenants_query.all()
    delete_forms = {}
    for tenant in tenants_list:
        delete_instance = DeleteTenantForm()
        delete_instance.tenant_id.data = tenant.id
        delete_forms[tenant.id] = delete_instance
    return render_template(
        "core/tenants_list.html",
        tenants=tenants_list,
        form=form,
        selected_property_id=selected_property_id,
        delete_forms=delete_forms,
        editing_tenant=editing_tenant,
    )


@core_bp.route("/leases", methods=["GET", "POST"])
@login_required
def leases():
    """契約の一覧＋フォーム。物件/部屋に応じて入居者候補を自動選択する。"""
    form = LeaseForm()
    properties = Property.query.order_by(Property.name).all()
    tenants = Tenant.query.order_by(Tenant.name).all()
    # SelectField の選択肢は都度再構築し、未登録時は警告を出す。
    properties_choices = [(prop.id, prop.name) for prop in properties]
    form.property_id.choices = properties_choices

    if request.method == "GET":
        # GET 初期表示では開始日・ステータスに既定値を入れておく。
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

    # 物件ごとの入居者一覧から号室の選択肢を構築する。
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
        # 編集時は既存の号室や値をそのままフォームに差し戻す。
        if editing_lease.unit_number and editing_lease.unit_number not in valid_units:
            form.unit_number.choices.append((editing_lease.unit_number, editing_lease.unit_number))
            valid_units.add(editing_lease.unit_number)
        form.submit.label.text = "契約を更新"
        if request.method != "POST":
            form.lease_id.data = str(editing_lease.id)
            form.property_id.data = editing_lease.property_id
            form.unit_number.data = editing_lease.unit_number or ""
            form.tenant_id.data = str(editing_lease.tenant_id)
            form.tenant_display.data = editing_lease.tenant.name if editing_lease.tenant else ""
            form.rent.data = float(editing_lease.rent or 0) / 10000
            form.start_date.data = editing_lease.start_date
            form.end_date.data = editing_lease.end_date
            form.status.data = editing_lease.status
    else:
        form.submit.label.text = "契約を保存"
        form.lease_id.data = ""

    if request.method == "POST" and (not properties_choices or not tenants):
        flash("契約を作成する前に物件と入居者を登録してください。", "warning")
        return redirect(url_for("core.leases"))

    # hidden lease_id の有無で更新/新規を判定し、必要に応じて既存契約を上書き。
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

    lease_query = (
        Lease.query.options(
            joinedload(Lease.property),
            joinedload(Lease.tenant),
        )
        .join(Property)
        .order_by(Property.name.asc(), Lease.unit_number.asc(), Lease.start_date.desc())
    )

    # 一覧は選択された物件で絞り込み可能。
    if selected_property_id is not None:
        lease_query = lease_query.filter(Lease.property_id == selected_property_id)

    leases_list = lease_query.all()

    occupied_keys = {
        (lease.property_id, lease.unit_number)
        for lease in leases_list
        if lease.property_id is not None and lease.unit_number
    }

    vacancy_rows: list[SimpleNamespace] = []
    for tenant in tenants:
        if tenant.property_id is None or not tenant.unit_number:
            continue
        if tenant.name.strip() != "空室":
            continue
        if selected_property_id is not None and tenant.property_id != selected_property_id:
            continue
        key = (tenant.property_id, tenant.unit_number)
        if key in occupied_keys:
            continue
        vacancy_rows.append(
            SimpleNamespace(
                id=None,
                property=tenant.property,
                property_id=tenant.property_id,
                unit_number=tenant.unit_number,
                tenant=tenant,
                rent=None,
                status="空室",
                start_date=None,
                end_date=None,
                is_vacancy=True,
            ),
        )

    if vacancy_rows:
        date_min_ordinal = date.min.toordinal()

        def lease_sort_key(lease: Lease | SimpleNamespace) -> tuple[str, str, int, int]:
            property_name = lease.property.name if getattr(lease, "property", None) else ""
            unit_value = lease.unit_number or ""
            is_vacancy = 1 if getattr(lease, "is_vacancy", False) else 0
            start_date = getattr(lease, "start_date", None)
            if isinstance(start_date, date):
                start_ordinal = -start_date.toordinal()
            else:
                start_ordinal = -date_min_ordinal
            return (property_name, unit_value, is_vacancy, start_ordinal)

        leases_list = sorted([*leases_list, *vacancy_rows], key=lease_sort_key)

    # 前面の JavaScript で物件 -> (入居者, 号室) を引き当てるための辞書。
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
@core_bp.route("/tenants/<int:tenant_id>/delete", methods=["POST"])
@login_required
def delete_tenant(tenant_id: int):
    form = DeleteTenantForm()
    # CSRF + hidden で二重送信を防ぎ、安全に対象レコードを特定する。
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
    next_url = form.next_url.data or request.form.get("next_url")
    if next_url:
        parsed = urlparse(next_url)
        if not parsed.netloc and parsed.path:
            return redirect(next_url)
    return redirect(url_for("core.leases"))
