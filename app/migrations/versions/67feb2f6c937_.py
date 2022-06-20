"""empty message

Revision ID: 67feb2f6c937
Revises: 600996305d17
Create Date: 2022-06-16 08:01:48.830834

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '67feb2f6c937'
down_revision = '600996305d17'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('search_results')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('search_results',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('row_entry_date', sa.VARCHAR(length=32), nullable=True),
    sa.Column('row_update_date', sa.VARCHAR(length=32), nullable=True),
    sa.Column('search_item_id', sa.INTEGER(), nullable=True),
    sa.Column('search_id', sa.INTEGER(), nullable=True),
    sa.ForeignKeyConstraint(['search_id'], ['user_search_item.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###
