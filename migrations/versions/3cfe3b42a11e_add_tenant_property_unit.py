"""テナントに property unit を追加

Revision ID: 3cfe3b42a11e
Revises: 7e2bfc4341a1
Create Date: 2025-10-19 18:59:53.497864

"""
from alembic import op
import sqlalchemy as sa


# Alembic が利用するリビジョン識別子。
revision = '3cfe3b42a11e'
down_revision = '7e2bfc4341a1'
branch_labels = None
depends_on = None


def upgrade():
    # ### Alembic が自動生成したコマンド。必要があれば調整してください。 ###
    with op.batch_alter_table('tenant', schema=None) as batch_op:
        batch_op.add_column(sa.Column('property_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('unit_number', sa.String(length=50), nullable=True))
        batch_op.create_foreign_key(
            'fk_tenant_property_id',
            'property',
            ['property_id'],
            ['id'],
        )

    # ### Alembic コマンドここまで ###


def downgrade():
    # ### Alembic が自動生成したコマンド。必要があれば調整してください。 ###
    with op.batch_alter_table('tenant', schema=None) as batch_op:
        batch_op.drop_constraint('fk_tenant_property_id', type_='foreignkey')
        batch_op.drop_column('unit_number')
        batch_op.drop_column('property_id')

    # ### Alembic コマンドここまで ###
