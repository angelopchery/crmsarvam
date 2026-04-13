"""
Pydantic schemas for Intelligence models (FollowUp, Deadline, Task).
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


class FollowUpBase(BaseModel):
    """Base schema for FollowUp."""

    description: str = Field(..., min_length=1)
    date: Optional[datetime] = None


class FollowUpCreate(FollowUpBase):
    """Schema for creating a new follow-up."""

    event_id: int


class FollowUpUpdate(BaseModel):
    """Schema for updating a follow-up."""

    description: Optional[str] = Field(None, min_length=1)
    date: Optional[datetime] = None


class FollowUpResponse(FollowUpBase):
    """Schema for follow-up response."""

    id: int
    event_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeadlineBase(BaseModel):
    """Base schema for Deadline."""

    description: str = Field(..., min_length=1)
    due_date: datetime


class DeadlineCreate(DeadlineBase):
    """Schema for creating a new deadline."""

    event_id: int


class DeadlineUpdate(BaseModel):
    """Schema for updating a deadline."""

    description: Optional[str] = Field(None, min_length=1)
    due_date: Optional[datetime] = None


class DeadlineResponse(DeadlineBase):
    """Schema for deadline response."""

    id: int
    event_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskBase(BaseModel):
    """Base schema for Task."""

    status: Literal["pending", "completed"] = "pending"


class TaskCreate(TaskBase):
    """Schema for creating a new task."""

    deadline_id: int


class TaskUpdate(BaseModel):
    """Schema for updating a task."""

    status: Optional[Literal["pending", "completed"]] = None


class TaskResponse(TaskBase):
    """Schema for task response."""

    id: int
    deadline_id: int
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskWithDeadline(TaskResponse):
    """Schema for task response with deadline details."""

    deadline_description: str
    deadline_due_date: datetime
    event_id: int
    event_title: Optional[str] = None


class FollowUpListResponse(BaseModel):
    """Schema for paginated follow-up list response."""

    follow_ups: list[FollowUpResponse]
    total: int
    page: int
    page_size: int


class DeadlineListResponse(BaseModel):
    """Schema for paginated deadline list response."""

    deadlines: list[DeadlineResponse]
    total: int
    page: int
    page_size: int


class TaskListResponse(BaseModel):
    """Schema for paginated task list response."""

    tasks: list[TaskResponse]
    total: int
    page: int
    page_size: int
