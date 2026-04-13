"""
Intelligence router for follow-ups, deadlines, and tasks management.
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.routers.auth import get_current_user
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
from app.schemas.user import UserResponse
from app.services.intelligence_service import (
    FollowUpService,
    DeadlineService,
    TaskService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])


# ============ Follow-Up Routes ============

@router.get("/follow-ups", response_model=FollowUpListResponse)
async def get_follow_ups(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    event_id: Annotated[int, Query(description="Filter by event ID")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Number of records to return")] = 100,
):
    """
    Get paginated list of follow-ups.

    Requires: Any authenticated user
    If event_id is provided, returns follow-ups for that event only.
    """
    follow_up_service = FollowUpService(db)

    if event_id:
        return await follow_up_service.get_follow_ups_by_event(event_id, skip=skip, limit=limit)

    # If no event_id, return empty list (follow-ups are always tied to an event)
    return FollowUpListResponse(follow_ups=[], total=0, page=1, page_size=limit)


@router.get("/follow-ups/{follow_up_id}", response_model=FollowUpResponse)
async def get_follow_up(
    follow_up_id: int,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific follow-up by ID.

    Requires: Any authenticated user
    """
    follow_up_service = FollowUpService(db)
    follow_up = await follow_up_service.get_follow_up(follow_up_id)

    if not follow_up:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow-up not found",
        )

    return follow_up


@router.post("/follow-ups", response_model=FollowUpResponse, status_code=status.HTTP_201_CREATED)
async def create_follow_up(
    follow_up_data: FollowUpCreate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new follow-up.

    Requires: Any authenticated user
    """
    follow_up_service = FollowUpService(db)

    try:
        follow_up = await follow_up_service.create_follow_up(follow_up_data)
        return follow_up
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/follow-ups/{follow_up_id}", response_model=FollowUpResponse)
async def update_follow_up(
    follow_up_id: int,
    follow_up_data: FollowUpUpdate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update an existing follow-up.

    Requires: Any authenticated user
    """
    follow_up_service = FollowUpService(db)

    try:
        follow_up = await follow_up_service.update_follow_up(follow_up_id, follow_up_data)
        return follow_up
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/follow-ups/{follow_up_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_follow_up(
    follow_up_id: int,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a follow-up.

    Requires: Any authenticated user
    """
    follow_up_service = FollowUpService(db)
    deleted = await follow_up_service.delete_follow_up(follow_up_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow-up not found",
        )


# ============ Deadline Routes ============

@router.get("/deadlines", response_model=DeadlineListResponse)
async def get_deadlines(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    event_id: Annotated[int, Query(description="Filter by event ID")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Number of records to return")] = 100,
):
    """
    Get paginated list of deadlines.

    Requires: Any authenticated user
    If event_id is provided, returns deadlines for that event only.
    Otherwise, returns upcoming deadlines sorted by due date.
    """
    deadline_service = DeadlineService(db)

    if event_id:
        return await deadline_service.get_deadlines_by_event(event_id, skip=skip, limit=limit)

    # Return upcoming deadlines
    return await deadline_service.get_upcoming_deadlines(skip=skip, limit=limit)


@router.get("/deadlines/{deadline_id}", response_model=DeadlineResponse)
async def get_deadline(
    deadline_id: int,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific deadline by ID.

    Requires: Any authenticated user
    """
    deadline_service = DeadlineService(db)
    deadline = await deadline_service.get_deadline(deadline_id)

    if not deadline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deadline not found",
        )

    return deadline


@router.post("/deadlines", response_model=DeadlineResponse, status_code=status.HTTP_201_CREATED)
async def create_deadline(
    deadline_data: DeadlineCreate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new deadline.

    Requires: Any authenticated user
    Note: This automatically creates a pending task for the deadline.
    """
    deadline_service = DeadlineService(db)

    try:
        deadline = await deadline_service.create_deadline(deadline_data)
        return deadline
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/deadlines/{deadline_id}", response_model=DeadlineResponse)
async def update_deadline(
    deadline_id: int,
    deadline_data: DeadlineUpdate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update an existing deadline.

    Requires: Any authenticated user
    """
    deadline_service = DeadlineService(db)

    try:
        deadline = await deadline_service.update_deadline(deadline_id, deadline_data)
        return deadline
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/deadlines/{deadline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deadline(
    deadline_id: int,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a deadline.

    Requires: Any authenticated user
    Note: This will cascade delete the associated task.
    """
    deadline_service = DeadlineService(db)
    deleted = await deadline_service.delete_deadline(deadline_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deadline not found",
        )


# ============ Task Routes ============

@router.get("/tasks", response_model=list[TaskWithDeadline])
async def get_tasks(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: Annotated[str | None, Query(description="Filter by status (pending/completed)")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Number of records to return")] = 100,
):
    """
    Get all tasks with their associated deadline and event details.

    This endpoint returns tasks sorted by deadline due date (ascending).
    These tasks are used for the calendar/to-do view.

    Requires: Any authenticated user
    """
    task_service = TaskService(db)
    tasks = await task_service.get_tasks_with_deadlines(
        skip=skip,
        limit=limit,
        status=status,
    )
    return tasks


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific task by ID.

    Requires: Any authenticated user
    """
    task_service = TaskService(db)
    task = await task_service.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return task


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new task.

    Requires: Any authenticated user
    """
    task_service = TaskService(db)

    try:
        task = await task_service.create_task(task_data)
        return task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update an existing task.

    Requires: Any authenticated user
    Use this to mark tasks as completed.
    """
    task_service = TaskService(db)

    try:
        task = await task_service.update_task(task_id, task_data)
        return task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a task.

    Requires: Any authenticated user
    """
    task_service = TaskService(db)
    deleted = await task_service.delete_task(task_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
