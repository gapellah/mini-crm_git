"""開発やデモ向けにサンプルデータを投入するユーティリティ。"""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from .extensions import db
from .models import Lease, LeaseStatus, Property, Tenant


def _month_start(reference: date, months_ago: int) -> date:
    year = reference.year
    month = reference.month - months_ago
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def seed_data(with_reset: bool = False) -> None:
    if with_reset:
        Lease.query.delete()
        Tenant.query.delete()
        Property.query.delete()
        db.session.commit()

    if Property.query.count() > 0 and not with_reset:
        return

    property_blueprints = [
        ("サンライトタワー", "東京都中央区1-2-3", "駅徒歩5分のハイグレードマンション"),
        ("ベルビューガーデン", "東京都世田谷区4-5-6", "ファミリー向け低層物件"),
        ("グリーンパークヒルズ", "神奈川県横浜市青葉区7-8-9", "駐車場・駐輪場完備"),
        ("コスモレジデンス", "千葉県船橋市1-9-5", "SOHO向けオフィス併設"),
        ("ブリーズハイツ", "埼玉県さいたま市南区3-4-7", "閑静な住宅街に位置"),
        ("メトロシティ新宿", "東京都新宿区5-6-2", "24時間コンシェルジュ"),
        ("リバーサイド桜川", "東京都墨田区8-1-11", "リバーサイドビュー"),
        ("シーサイドラグーン", "神奈川県藤沢市2-3-8", "海まで徒歩3分"),
    ]

    properties: list[Property] = []
    for name, address, note in property_blueprints:
        property_obj = Property(name=name, address=address, note=note)
        db.session.add(property_obj)
        properties.append(property_obj)

    db.session.flush()

    unit_templates = ["101", "102", "201", "202", "301", "302"]
    tenant_index = 1
    tenants: list[Tenant] = []
    for property_obj in properties:
        for unit_number in unit_templates:
            tenant = Tenant(
                property=property_obj,
                unit_number=unit_number,
                name=f"入居者{tenant_index:03d}",
                email=f"tenant{tenant_index:03d}@example.com",
                phone=f"090-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
            )
            db.session.add(tenant)
            tenants.append(tenant)
            tenant_index += 1

    db.session.flush()

    today = date.today()
    statuses = [
        LeaseStatus.ACTIVE,
        LeaseStatus.PENDING,
        LeaseStatus.TERMINATED,
    ]

    lease_id = 1
    for months_ago in range(24, -1, -1):
        start_on = _month_start(today, months_ago)
        end_on = start_on + timedelta(days=330)
        tenant = random.choice(tenants)
        lease = Lease(
            property=tenant.property,
            tenant=tenant,
            unit_number=tenant.unit_number,
            rent=Decimal(random.randint(7, 18)) * Decimal("10000"),
            start_date=start_on,
            end_date=end_on if random.random() < 0.3 else None,
            status=random.choice(statuses),
        )
        db.session.add(lease)
        lease_id += 1

    db.session.commit()
