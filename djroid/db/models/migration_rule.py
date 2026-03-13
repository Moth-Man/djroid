"""Migration rule model for storing file migration rules."""

from typing import Optional
from sqlalchemy import Integer, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped
from datetime import datetime, UTC
import uuid
from ..session import Base


class MigrationRule(Base):
    """Model for storing migration rules that map metadata to destination directories."""

    __tablename__ = "migration_rules"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Rule definition
    metadata_tag: Mapped[str] = mapped_column(String, nullable=False, index=True)
    metadata_value: Mapped[str] = mapped_column(String, nullable=False, index=True)
    destination_directory: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional rule name/description
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Rule priority (lower = higher priority)
    priority: Mapped[int] = mapped_column(Integer, default=0, index=True)

    # Whether this rule is enabled
    enabled: Mapped[bool] = mapped_column(default=True, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(UTC),
        onupdate=datetime.now(UTC)
    )

    def __repr__(self) -> str:
        return f"<MigrationRule {self.metadata_tag}:{self.metadata_value} -> {self.destination_directory}>"
