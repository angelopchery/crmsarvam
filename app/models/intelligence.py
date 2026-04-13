"""
Intelligence models for follow-ups, deadlines, and tasks.
"""
from datetime import datetime, date

from sqlalchemy import String, Text, ForeignKey, Date, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FollowUp(Base):
    """
    FollowUp model for tracking action items from events.

    Attributes:
        id: Primary key
        event_id: Foreign key to events table
        description: Follow-up description
        date: Optional follow-up date
        created_at: Record creation timestamp
    """

    __tablename__ = "follow_ups"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="follow_ups")

    def __repr__(self) -> str:
        return f"<FollowUp(id={self.id}, event_id={self.event_id})>"


class Deadline(Base):
    """
    Deadline model for tracking due dates from events.

    Attributes:
        id: Primary key
        event_id: Foreign key to events table
        description: Deadline description
        due_date: Due date
        created_at: Record creation timestamp
    """

    __tablename__ = "deadlines"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="deadlines")
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="deadline", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Deadline(id={self.id}, due_date={self.due_date}, event_id={self.event_id})>"


class Task(Base):
    """
    Task model for tracking completion of deadlines.

    Attributes:
        id: Primary key
        deadline_id: Foreign key to deadlines table
        status: Task status (pending, completed)
        completed_at: Task completion timestamp
        created_at: Record creation timestamp
    """

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    deadline_id: Mapped[int] = mapped_column(
        ForeignKey("deadlines.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    # Relationships
    deadline: Mapped["Deadline"] = relationship(back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, status='{self.status}', deadline_id={self.deadline_id})>"
