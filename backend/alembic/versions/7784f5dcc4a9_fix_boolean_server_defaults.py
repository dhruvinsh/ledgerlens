"""fix_boolean_server_defaults

Revision ID: 7784f5dcc4a9
Revises: c11f3c9ec32f
Create Date: 2026-04-05 00:58:56.701294

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7784f5dcc4a9"
down_revision: Union[str, Sequence[str], None] = "c11f3c9ec32f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("line_items", schema=None) as batch_op:
        batch_op.alter_column("is_refund", server_default=sa.text("false"))

    with op.batch_alter_table("receipts", schema=None) as batch_op:
        batch_op.alter_column("is_refund", server_default=sa.text("false"))

    with op.batch_alter_table("model_configs", schema=None) as batch_op:
        batch_op.alter_column("supports_vision", server_default=sa.text("false"))


def downgrade() -> None:
    with op.batch_alter_table("line_items", schema=None) as batch_op:
        batch_op.alter_column("is_refund", server_default=sa.text("0"))

    with op.batch_alter_table("receipts", schema=None) as batch_op:
        batch_op.alter_column("is_refund", server_default=sa.text("0"))

    with op.batch_alter_table("model_configs", schema=None) as batch_op:
        batch_op.alter_column("supports_vision", server_default=sa.text("0"))
