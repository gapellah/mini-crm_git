"""Lease に unit number を追加

Revision ID: 7e2bfc4341a1
Revises: 813add7d48fb
Create Date: 2025-10-19 17:59:10.005677

"""
from alembic import op
import sqlalchemy as sa


# Alembic が利用するリビジョン識別子。
revision = '7e2bfc4341a1'
down_revision = '813add7d48fb'
branch_labels = None
depends_on = None


def upgrade():
    # ### Alembic が自動生成したコマンド。必要があれば調整してください。 ###
    with op.batch_alter_table('lease', schema=None) as batch_op:
        batch_op.add_column(sa.Column('unit_number', sa.String(length=50), nullable=True))

    # ### Alembic コマンドここまで ###


def downgrade():
    # ### Alembic が自動生成したコマンド。必要があれば調整してください。 ###
    with op.batch_alter_table('lease', schema=None) as batch_op:
        batch_op.drop_column('unit_number')

    # ### Alembic コマンドここまで ###
