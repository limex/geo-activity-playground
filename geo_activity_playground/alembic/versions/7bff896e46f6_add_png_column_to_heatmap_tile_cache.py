from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7bff896e46f6'
down_revision: Union[str, None] = 'a8f7b809daf8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('heatmap_tile_cache', schema=None) as batch_op:
        batch_op.add_column(sa.Column('png', sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('heatmap_tile_cache', schema=None) as batch_op:
        batch_op.drop_column('png')
