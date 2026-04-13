"""
Pydantic schemas for Client and POC models.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class ClientBase(BaseModel):
    """Base schema for Client."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class ClientCreate(ClientBase):
    """Schema for creating a new client."""

    pass


class ClientUpdate(BaseModel):
    """Schema for updating a client."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None


class ClientResponse(ClientBase):
    """Schema for client response."""

    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClientWithDetails(ClientResponse):
    """Schema for client response with related data."""

    pocs: list["POCResponse"] = []
    events_count: int = 0


class POCBase(BaseModel):
    """Base schema for POC (Point of Contact)."""

    name: str = Field(..., min_length=1, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    additional_info: Optional[str] = None


class POCCreate(POCBase):
    """Schema for creating a new POC."""

    client_id: int


class POCUpdate(BaseModel):
    """Schema for updating a POC."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    additional_info: Optional[str] = None


class POCResponse(POCBase):
    """Schema for POC response."""

    id: int
    client_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClientListResponse(BaseModel):
    """Schema for paginated client list response."""

    clients: list[ClientResponse]
    total: int
    page: int
    page_size: int


class POCListResponse(BaseModel):
    """Schema for paginated POC list response."""

    pocs: list[POCResponse]
    total: int
    page: int
    page_size: int


# Forward reference resolution
ClientWithDetails.model_rebuild()
