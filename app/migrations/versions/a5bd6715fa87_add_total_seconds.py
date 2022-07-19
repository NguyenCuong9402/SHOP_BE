"""add total_seconds

Revision ID: a5bd6715fa87
Revises: 9b734dca5745
Create Date: 2022-07-15 10:58:14.299218

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a5bd6715fa87'
down_revision = '9b734dca5745'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('map_test_exec', sa.Column('total_seconds', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('map_test_exec', 'total_seconds')
    # ### end Alembic commands ###