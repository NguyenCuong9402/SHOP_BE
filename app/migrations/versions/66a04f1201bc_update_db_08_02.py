"""update db 08-02

Revision ID: 66a04f1201bc
Revises: 4c3c8ed58ec6
Create Date: 2023-02-08 10:29:47.892670

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '66a04f1201bc'
down_revision = '4c3c8ed58ec6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('test_run_ibfk_2', 'test_run', type_='foreignkey')
    op.create_foreign_key(None, 'test_run', 'test_status', ['test_status_id'], ['id'], onupdate='SET NULL', ondelete='SET NULL')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'test_run', type_='foreignkey')
    op.create_foreign_key('test_run_ibfk_2', 'test_run', 'test_status', ['test_status_id'], ['id'])
    # ### end Alembic commands ###