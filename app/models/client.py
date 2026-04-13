"""
Client and POC models for customer management.
"""
from datetime import datetime

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Client(Base):
    """
    Client model representing a company or organization.

    Attributes:
        id: Primary key
        name: Client company name
        description: Additional information about client
        created_at: Record creation timestamp
    """

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    # Relationships
    pocs: Mapped[list["POC"]] = relationship(
        back_populates="client", lazy="selectin", cascade="all, delete-orphan"
    )
    events: Mapped[list["Event"]] = relationship(
        back_populates="client", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Client(id={self.id}, name='{self.name}')>"


class POC(Base):
    """
    Point of Contact model for client representatives.

    Attributes:
        id: Primary key
        client_id: Foreign key to clients table
        name: POC name
        phone: Phone number
        additional_info: Additional contact information
        created_at: Record creation timestamp
    """

    __tablename__ = "pocs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    additional_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    # Relationships
    client: Mapped["Client"] = relationship(back_populates="pocs")

    # Indexes
    __table_args__ = (
        {"schema": None},  # No explicit schema
    )

    def __repr__(self) -> str:
        return f"<POC(id={self.id}, name='{self.name}', client_id={self.client_id})>"
