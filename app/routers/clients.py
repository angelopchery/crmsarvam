"""
Client and POC management routers for CRUD operations.
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.routers.auth import get_current_user
from app.schemas.client import (
    ClientCreate,
    ClientUpdate,
    ClientResponse,
    ClientWithDetails,
    ClientListResponse,
    POCCreate,
    POCUpdate,
    POCResponse,
    POCListResponse,
)
from app.schemas.user import UserResponse
from app.services.client_service import ClientService, POCService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/clients", tags=["clients"])

# Include POC routes
poc_router = APIRouter(prefix="/api/pocs", tags=["pocs"])


# ============ Client Routes ============

@router.get("", response_model=ClientListResponse)
async def get_clients(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Number of records to return")] = 100,
    search: Annotated[str | None, Query(description="Search term for client name")] = None,
):
    """
    Get paginated list of clients.

    Requires: Any authenticated user
    """
    client_service = ClientService(db)
    return await client_service.get_clients(skip=skip, limit=limit, search=search)


@router.get("/{client_id}", response_model=ClientWithDetails)
async def get_client(
    client_id: int,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific client with POCs and events count.

    Requires: Any authenticated user
    """
    client_service = ClientService(db)
    client = await client_service.get_client_with_details(client_id)

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    return client


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    client_data: ClientCreate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new client.

    Requires: Any authenticated user
    """
    client_service = ClientService(db)
    client = await client_service.create_client(client_data)
    return client


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    client_data: ClientUpdate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update an existing client.

    Requires: Any authenticated user
    """
    client_service = ClientService(db)

    try:
        client = await client_service.update_client(client_id, client_data)
        return client
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: int,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a client.

    Requires: Any authenticated user
    Note: This will cascade delete all related POCs, events, etc.
    """
    client_service = ClientService(db)
    deleted = await client_service.delete_client(client_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )


# ============ POC Routes ============

@poc_router.get("", response_model=POCListResponse)
async def get_pocs_by_client(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    client_id: Annotated[int, Query(description="Filter by client ID")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Number of records to return")] = 100,
):
    """
    Get paginated list of POCs.

    Requires: Any authenticated user
    If client_id is provided, returns POCs for that client only.
    """
    poc_service = POCService(db)

    if client_id:
        return await poc_service.get_pocs_by_client(client_id, skip=skip, limit=limit)

    # If no client_id, return empty list (POCs are always tied to a client)
    return POCListResponse(pocs=[], total=0, page=1, page_size=limit)


@poc_router.get("/{poc_id}", response_model=POCResponse)
async def get_poc(
    poc_id: int,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific POC by ID.

    Requires: Any authenticated user
    """
    poc_service = POCService(db)
    poc = await poc_service.get_poc(poc_id)

    if not poc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="POC not found",
        )

    return poc


@poc_router.post("", response_model=POCResponse, status_code=status.HTTP_201_CREATED)
async def create_poc(
    poc_data: POCCreate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new POC.

    Requires: Any authenticated user
    """
    poc_service = POCService(db)

    try:
        poc = await poc_service.create_poc(poc_data)
        return poc
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@poc_router.put("/{poc_id}", response_model=POCResponse)
async def update_poc(
    poc_id: int,
    poc_data: POCUpdate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update an existing POC.

    Requires: Any authenticated user
    """
    poc_service = POCService(db)

    try:
        poc = await poc_service.update_poc(poc_id, poc_data)
        return poc
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@poc_router.delete("/{poc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_poc(
    poc_id: int,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a POC.

    Requires: Any authenticated user
    """
    poc_service = POCService(db)
    deleted = await poc_service.delete_poc(poc_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="POC not found",
        )
