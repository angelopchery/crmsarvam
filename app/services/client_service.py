"""
Client and POC management service for CRUD operations.
"""
import logging
from typing import Optional

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.client import Client, POC
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

logger = logging.getLogger(__name__)


class ClientService:
    """Service for handling Client CRUD operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize ClientService with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_client(self, client_id: int) -> Optional[ClientResponse]:
        """
        Get client by ID.

        Args:
            client_id: Client ID

        Returns:
            Client response or None
        """
        result = await self.db.execute(
            select(Client).where(Client.id == client_id)
        )
        client = result.scalar_one_or_none()
        return ClientResponse.model_validate(client) if client else None

    async def get_client_with_details(self, client_id: int) -> Optional[ClientWithDetails]:
        """
        Get client with POCs and events count.

        Args:
            client_id: Client ID

        Returns:
            Client with details response or None
        """
        result = await self.db.execute(
            select(Client)
            .options(selectinload(Client.pocs))
            .where(Client.id == client_id)
        )
        client = result.scalar_one_or_none()

        if not client:
            return None

        # Count events
        from app.models.event import Event
        events_result = await self.db.execute(
            select(func.count()).select_from(Event).where(Event.client_id == client_id)
        )
        events_count = events_result.scalar()

        return ClientWithDetails(
            id=client.id,
            name=client.name,
            description=client.description,
            created_at=client.created_at,
            pocs=[POCResponse.model_validate(poc) for poc in client.pocs],
            events_count=events_count,
        )

    async def get_clients(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> ClientListResponse:
        """
        Get paginated list of clients.

        Args:
            skip: Number of records to skip
            limit: Number of records to return
            search: Optional search term for client name

        Returns:
            Paginated client list response
        """
        # Build query
        query = select(Client)
        if search:
            query = query.where(Client.name.ilike(f"%{search}%"))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Get clients with pagination
        query = query.offset(skip).limit(limit).order_by(Client.created_at.desc())
        result = await self.db.execute(query)
        clients = result.scalars().all()

        return ClientListResponse(
            clients=[ClientResponse.model_validate(client) for client in clients],
            total=total,
            page=skip // limit + 1,
            page_size=limit,
        )

    async def create_client(self, client_data: ClientCreate) -> ClientResponse:
        """
        Create a new client.

        Args:
            client_data: Client creation data

        Returns:
            Created client response
        """
        client = Client(**client_data.model_dump())
        self.db.add(client)
        await self.db.commit()
        await self.db.refresh(client)

        logger.info(f"Client created: {client.name}")
        return ClientResponse.model_validate(client)

    async def update_client(
        self, client_id: int, client_data: ClientUpdate
    ) -> Optional[ClientResponse]:
        """
        Update an existing client.

        Args:
            client_id: Client ID
            client_data: Client update data

        Returns:
            Updated client response or None

        Raises:
            ValueError: If client not found
        """
        # Get client
        result = await self.db.execute(
            select(Client).where(Client.id == client_id)
        )
        client = result.scalar_one_or_none()

        if not client:
            raise ValueError("Client not found")

        # Update fields
        update_data = client_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(client, field, value)

        await self.db.commit()
        await self.db.refresh(client)

        logger.info(f"Client updated: {client.name}")
        return ClientResponse.model_validate(client)

    async def delete_client(self, client_id: int) -> bool:
        """
        Delete a client.

        Args:
            client_id: Client ID

        Returns:
            True if deleted, False otherwise
        """
        result = await self.db.execute(
            delete(Client).where(Client.id == client_id)
        )
        await self.db.commit()
        deleted = result.rowcount > 0

        if deleted:
            logger.info(f"Client deleted: {client_id}")

        return deleted


class POCService:
    """Service for handling POC CRUD operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize POCService with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_poc(self, poc_id: int) -> Optional[POCResponse]:
        """
        Get POC by ID.

        Args:
            poc_id: POC ID

        Returns:
            POC response or None
        """
        result = await self.db.execute(select(POC).where(POC.id == poc_id))
        poc = result.scalar_one_or_none()
        return POCResponse.model_validate(poc) if poc else None

    async def get_pocs_by_client(
        self,
        client_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> POCListResponse:
        """
        Get POCs for a specific client.

        Args:
            client_id: Client ID
            skip: Number of records to skip
            limit: Number of records to return

        Returns:
            Paginated POC list response
        """
        # Get total count
        count_query = select(func.count()).where(POC.client_id == client_id)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Get POCs with pagination
        query = (
            select(POC)
            .where(POC.client_id == client_id)
            .offset(skip)
            .limit(limit)
            .order_by(POC.created_at.desc())
        )
        result = await self.db.execute(query)
        pocs = result.scalars().all()

        return POCListResponse(
            pocs=[POCResponse.model_validate(poc) for poc in pocs],
            total=total,
            page=skip // limit + 1,
            page_size=limit,
        )

    async def create_poc(self, poc_data: POCCreate) -> POCResponse:
        """
        Create a new POC.

        Args:
            poc_data: POC creation data

        Returns:
            Created POC response

        Raises:
            ValueError: If client not found
        """
        # Verify client exists
        client_result = await self.db.execute(
            select(Client).where(Client.id == poc_data.client_id)
        )
        if not client_result.scalar_one_or_none():
            raise ValueError("Client not found")

        poc = POC(**poc_data.model_dump())
        self.db.add(poc)
        await self.db.commit()
        await self.db.refresh(poc)

        logger.info(f"POC created: {poc.name}")
        return POCResponse.model_validate(poc)

    async def update_poc(
        self, poc_id: int, poc_data: POCUpdate
    ) -> Optional[POCResponse]:
        """
        Update an existing POC.

        Args:
            poc_id: POC ID
            poc_data: POC update data

        Returns:
            Updated POC response or None

        Raises:
            ValueError: If POC not found
        """
        # Get POC
        result = await self.db.execute(select(POC).where(POC.id == poc_id))
        poc = result.scalar_one_or_none()

        if not poc:
            raise ValueError("POC not found")

        # Update fields
        update_data = poc_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(poc, field, value)

        await self.db.commit()
        await self.db.refresh(poc)

        logger.info(f"POC updated: {poc.name}")
        return POCResponse.model_validate(poc)

    async def delete_poc(self, poc_id: int) -> bool:
        """
        Delete a POC.

        Args:
            poc_id: POC ID

        Returns:
            True if deleted, False otherwise
        """
        result = await self.db.execute(delete(POC).where(POC.id == poc_id))
        await self.db.commit()
        deleted = result.rowcount > 0

        if deleted:
            logger.info(f"POC deleted: {poc_id}")

        return deleted
