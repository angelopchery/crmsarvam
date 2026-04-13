"""
Intelligence service for handling follow-ups, deadlines, and tasks.
"""
import logging
from typing import Optional
from datetime import datetime

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import FollowUp, Deadline, Task
from app.models.event import Event
from app.schemas.intelligence import (
    FollowUpCreate,
    FollowUpUpdate,
    FollowUpResponse,
    FollowUpListResponse,
    DeadlineCreate,
    DeadlineUpdate,
    DeadlineResponse,
    DeadlineListResponse,
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
    TaskWithDeadline,
)

logger = logging.getLogger(__name__)


class FollowUpService:
    """Service for handling FollowUp CRUD operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize FollowUpService with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_follow_up(self, follow_up_id: int) -> Optional[FollowUpResponse]:
        """
        Get follow-up by ID.

        Args:
            follow_up_id: Follow-up ID

        Returns:
            Follow-up response or None
        """
        result = await self.db.execute(
            select(FollowUp).where(FollowUp.id == follow_up_id)
        )
        follow_up = result.scalar_one_or_none()
        return FollowUpResponse.model_validate(follow_up) if follow_up else None

    async def get_follow_ups_by_event(
        self,
        event_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> FollowUpListResponse:
        """
        Get follow-ups for a specific event.

        Args:
            event_id: Event ID
            skip: Number of records to skip
            limit: Number of records to return

        Returns:
            Paginated follow-up list response
        """
        # Get total count
        count_query = select(func.count()).where(FollowUp.event_id == event_id)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Get follow-ups with pagination
        query = (
            select(FollowUp)
            .where(FollowUp.event_id == event_id)
            .offset(skip)
            .limit(limit)
            .order_by(FollowUp.created_at.desc())
        )
        result = await self.db.execute(query)
        follow_ups = result.scalars().all()

        return FollowUpListResponse(
            follow_ups=[FollowUpResponse.model_validate(f) for f in follow_ups],
            total=total,
            page=skip // limit + 1,
            page_size=limit,
        )

    async def create_follow_up(self, follow_up_data: FollowUpCreate) -> FollowUpResponse:
        """
        Create a new follow-up.

        Args:
            follow_up_data: Follow-up creation data

        Returns:
            Created follow-up response

        Raises:
            ValueError: If event not found
        """
        # Verify event exists
        event_result = await self.db.execute(
            select(Event).where(Event.id == follow_up_data.event_id)
        )
        if not event_result.scalar_one_or_none():
            raise ValueError("Event not found")

        follow_up = FollowUp(**follow_up_data.model_dump())
        self.db.add(follow_up)
        await self.db.commit()
        await self.db.refresh(follow_up)

        logger.info(f"Follow-up created for event {follow_up.event_id}")
        return FollowUpResponse.model_validate(follow_up)

    async def update_follow_up(
        self, follow_up_id: int, follow_up_data: FollowUpUpdate
    ) -> Optional[FollowUpResponse]:
        """
        Update an existing follow-up.

        Args:
            follow_up_id: Follow-up ID
            follow_up_data: Follow-up update data

        Returns:
            Updated follow-up response or None

        Raises:
            ValueError: If follow-up not found
        """
        # Get follow-up
        result = await self.db.execute(
            select(FollowUp).where(FollowUp.id == follow_up_id)
        )
        follow_up = result.scalar_one_or_none()

        if not follow_up:
            raise ValueError("Follow-up not found")

        # Update fields
        update_data = follow_up_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(follow_up, field, value)

        await self.db.commit()
        await self.db.refresh(follow_up)

        logger.info(f"Follow-up updated: {follow_up_id}")
        return FollowUpResponse.model_validate(follow_up)

    async def delete_follow_up(self, follow_up_id: int) -> bool:
        """
        Delete a follow-up.

        Args:
            follow_up_id: Follow-up ID

        Returns:
            True if deleted, False otherwise
        """
        result = await self.db.execute(
            delete(FollowUp).where(FollowUp.id == follow_up_id)
        )
        await self.db.commit()
        deleted = result.rowcount > 0

        if deleted:
            logger.info(f"Follow-up deleted: {follow_up_id}")

        return deleted


class DeadlineService:
    """Service for handling Deadline CRUD operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize DeadlineService with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_deadline(self, deadline_id: int) -> Optional[DeadlineResponse]:
        """
        Get deadline by ID.

        Args:
            deadline_id: Deadline ID

        Returns:
            Deadline response or None
        """
        result = await self.db.execute(
            select(Deadline).where(Deadline.id == deadline_id)
        )
        deadline = result.scalar_one_or_none()
        return DeadlineResponse.model_validate(deadline) if deadline else None

    async def get_deadlines_by_event(
        self,
        event_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> DeadlineListResponse:
        """
        Get deadlines for a specific event.

        Args:
            event_id: Event ID
            skip: Number of records to skip
            limit: Number of records to return

        Returns:
            Paginated deadline list response
        """
        # Get total count
        count_query = select(func.count()).where(Deadline.event_id == event_id)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Get deadlines with pagination
        query = (
            select(Deadline)
            .where(Deadline.event_id == event_id)
            .offset(skip)
            .limit(limit)
            .order_by(Deadline.due_date.asc())
        )
        result = await self.db.execute(query)
        deadlines = result.scalars().all()

        return DeadlineListResponse(
            deadlines=[DeadlineResponse.model_validate(d) for d in deadlines],
            total=total,
            page=skip // limit + 1,
            page_size=limit,
        )

    async def get_upcoming_deadlines(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> DeadlineListResponse:
        """
        Get upcoming deadlines sorted by due date.

        Args:
            skip: Number of records to skip
            limit: Number of records to return

        Returns:
            Paginated deadline list response
        """
        # Get total count
        count_query = select(func.count()).where(Deadline.due_date >= datetime.utcnow())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Get upcoming deadlines
        query = (
            select(Deadline)
            .where(Deadline.due_date >= datetime.utcnow())
            .offset(skip)
            .limit(limit)
            .order_by(Deadline.due_date.asc())
        )
        result = await self.db.execute(query)
        deadlines = result.scalars().all()

        return DeadlineListResponse(
            deadlines=[DeadlineResponse.model_validate(d) for d in deadlines],
            total=total,
            page=skip // limit + 1,
            page_size=limit,
        )

    async def create_deadline(self, deadline_data: DeadlineCreate) -> DeadlineResponse:
        """
        Create a new deadline.

        Args:
            deadline_data: Deadline creation data

        Returns:
            Created deadline response

        Raises:
            ValueError: If event not found
        """
        # Verify event exists
        event_result = await self.db.execute(
            select(Event).where(Event.id == deadline_data.event_id)
        )
        if not event_result.scalar_one_or_none():
            raise ValueError("Event not found")

        deadline = Deadline(**deadline_data.model_dump())
        self.db.add(deadline)
        await self.db.commit()
        await self.db.refresh(deadline)

        # Create a pending task for this deadline
        task = Task(deadline_id=deadline.id, status="pending")
        self.db.add(task)
        await self.db.commit()

        logger.info(f"Deadline created for event {deadline.event_id}")
        return DeadlineResponse.model_validate(deadline)

    async def update_deadline(
        self, deadline_id: int, deadline_data: DeadlineUpdate
    ) -> Optional[DeadlineResponse]:
        """
        Update an existing deadline.

        Args:
            deadline_id: Deadline ID
            deadline_data: Deadline update data

        Returns:
            Updated deadline response or None

        Raises:
            ValueError: If deadline not found
        """
        # Get deadline
        result = await self.db.execute(
            select(Deadline).where(Deadline.id == deadline_id)
        )
        deadline = result.scalar_one_or_none()

        if not deadline:
            raise ValueError("Deadline not found")

        # Update fields
        update_data = deadline_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(deadline, field, value)

        await self.db.commit()
        await self.db.refresh(deadline)

        logger.info(f"Deadline updated: {deadline_id}")
        return DeadlineResponse.model_validate(deadline)

    async def delete_deadline(self, deadline_id: int) -> bool:
        """
        Delete a deadline.

        Args:
            deadline_id: Deadline ID

        Returns:
            True if deleted, False otherwise
        """
        result = await self.db.execute(
            delete(Deadline).where(Deadline.id == deadline_id)
        )
        await self.db.commit()
        deleted = result.rowcount > 0

        if deleted:
            logger.info(f"Deadline deleted: {deadline_id}")

        return deleted


class TaskService:
    """Service for handling Task CRUD operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize TaskService with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_task(self, task_id: int) -> Optional[TaskResponse]:
        """
        Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task response or None
        """
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        return TaskResponse.model_validate(task) if task else None

    async def get_tasks_by_deadline(
        self,
        deadline_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> TaskListResponse:
        """
        Get tasks for a specific deadline.

        Args:
            deadline_id: Deadline ID
            skip: Number of records to skip
            limit: Number of records to return

        Returns:
            Paginated task list response
        """
        # Get total count
        count_query = select(func.count()).where(Task.deadline_id == deadline_id)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Get tasks with pagination
        query = (
            select(Task)
            .where(Task.deadline_id == deadline_id)
            .offset(skip)
            .limit(limit)
            .order_by(Task.created_at.desc())
        )
        result = await self.db.execute(query)
        tasks = result.scalars().all()

        return TaskListResponse(
            tasks=[TaskResponse.model_validate(t) for t in tasks],
            total=total,
            page=skip // limit + 1,
            page_size=limit,
        )

    async def get_all_tasks(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> TaskListResponse:
        """
        Get all tasks with optional status filter.

        Args:
            skip: Number of records to skip
            limit: Number of records to return
            status: Optional status filter (pending/completed)

        Returns:
            Paginated task list response
        """
        # Build query
        query = select(Task)
        if status:
            query = query.where(Task.status == status)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Get tasks with pagination
        query = query.offset(skip).limit(limit).order_by(Task.created_at.desc())
        result = await self.db.execute(query)
        tasks = result.scalars().all()

        return TaskListResponse(
            tasks=[TaskResponse.model_validate(t) for t in tasks],
            total=total,
            page=skip // limit + 1,
            page_size=limit,
        )

    async def get_tasks_with_deadlines(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> list[TaskWithDeadline]:
        """
        Get tasks with their associated deadline and event details.

        Args:
            skip: Number of records to skip
            limit: Number of records to return
            status: Optional status filter (pending/completed)

        Returns:
            List of tasks with deadline details
        """
        # Build query
        from app.models.intelligence import Task, Deadline

        query = (
            select(Task, Deadline, Event)
            .join(Deadline, Task.deadline_id == Deadline.id)
            .join(Event, Deadline.event_id == Event.id)
        )

        if status:
            query = query.where(Task.status == status)

        # Get tasks with pagination
        query = (
            query.offset(skip)
            .limit(limit)
            .order_by(Deadline.due_date.asc())
        )
        result = await self.db.execute(query)
        rows = result.all()

        return [
            TaskWithDeadline(
                id=task.id,
                deadline_id=task.deadline_id,
                status=task.status,
                completed_at=task.completed_at,
                created_at=task.created_at,
                deadline_description=deadline.description,
                deadline_due_date=deadline.due_date,
                event_id=event.id,
                event_title=event.title,
            )
            for task, deadline, event in rows
        ]

    async def create_task(self, task_data: TaskCreate) -> TaskResponse:
        """
        Create a new task.

        Args:
            task_data: Task creation data

        Returns:
            Created task response

        Raises:
            ValueError: If deadline not found
        """
        # Verify deadline exists
        deadline_result = await self.db.execute(
            select(Deadline).where(Deadline.id == task_data.deadline_id)
        )
        if not deadline_result.scalar_one_or_none():
            raise ValueError("Deadline not found")

        task = Task(**task_data.model_dump())
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)

        logger.info(f"Task created for deadline {task.deadline_id}")
        return TaskResponse.model_validate(task)

    async def update_task(
        self, task_id: int, task_data: TaskUpdate
    ) -> Optional[TaskResponse]:
        """
        Update an existing task.

        Args:
            task_id: Task ID
            task_data: Task update data

        Returns:
            Updated task response or None

        Raises:
            ValueError: If task not found
        """
        # Get task
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            raise ValueError("Task not found")

        # Update fields
        update_data = task_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)

        # If marking as completed, set completed_at
        if task.status == "completed" and not task.completed_at:
            task.completed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(task)

        logger.info(f"Task updated: {task_id}")
        return TaskResponse.model_validate(task)

    async def delete_task(self, task_id: int) -> bool:
        """
        Delete a task.

        Args:
            task_id: Task ID

        Returns:
            True if deleted, False otherwise
        """
        result = await self.db.execute(delete(Task).where(Task.id == task_id))
        await self.db.commit()
        deleted = result.rowcount > 0

        if deleted:
            logger.info(f"Task deleted: {task_id}")

        return deleted
