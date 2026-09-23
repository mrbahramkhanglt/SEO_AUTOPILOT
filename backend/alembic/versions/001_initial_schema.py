"""Initial schema – tables also created via init_db() on startup for MVP.

Revision ID: 001
"""
from typing import Sequence, Union

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Prefer app.database.session.init_db() / Base.metadata.create_all for SQLite MVP.
    # Generate real migrations with: alembic revision --autogenerate
    pass


def downgrade() -> None:
    pass
