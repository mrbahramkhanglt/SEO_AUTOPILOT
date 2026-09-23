"""DB-agnostic column types (works with SQLite and PostgreSQL)."""
from sqlalchemy import JSON, String, TypeDecorator


class UUIDType(TypeDecorator):
    """Store UUID as string(36)."""
    impl = String(36)
    cache_ok = True

    def __init__(self, as_uuid: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)


JSONType = JSON
