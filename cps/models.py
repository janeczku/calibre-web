from __future__ import annotations

from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Field


class BookItem(BaseModel):
    """Represents a single book in list responses.

    Fields are intentionally small to keep the list payload light.
    """

    id: int = Field(..., description="Calibre book id")
    title: str = Field(..., description="Book title")
    sort: Optional[str] = Field(None, description="Sort title")
    author_sort: Optional[str] = Field(None, description="Primary author (sort order)")
    timestamp: Optional[datetime] = Field(None, description="Record creation timestamp (ISO 8601)")
    pubdate: Optional[datetime] = Field(None, description="Publication date (ISO 8601)")
    last_modified: Optional[datetime] = Field(None, description="Last modified timestamp (ISO 8601)")
    path: Optional[str] = Field(None, description="Library path for the book")
    has_cover: bool = Field(False, description="Whether a cover image exists")
    uuid: Optional[str] = Field(None, description="Calibre book UUID")

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 123,
                "title": "The Example Book",
                "sort": "Example, The",
                "author_sort": "Doe, John",
                "timestamp": "2023-01-01T12:00:00Z",
                "pubdate": "2022-12-01T12:00:00Z",
                "last_modified": "2023-02-01T10:30:00Z",
                "path": "Author/Example Book",
                "has_cover": True,
                "uuid": "550e8400-e29b-41d4-a716-446655440000",
            }
        }


class ListBooksResponse(BaseModel):
    """Response model for the `GET /books` endpoint."""

    page: int = Field(..., description="Page number (1-based)")
    per_page: int = Field(..., description="Items per page")
    total: int = Field(..., description="Total number of matching items")
    items: List[BookItem] = Field(..., description="List of books for this page")

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "page": 1,
                "per_page": 25,
                "total": 1234,
                "items": [
                    {
                        "id": 123,
                        "title": "The Example Book",
                        "sort": "Example, The",
                        "author_sort": "Doe, John",
                        "timestamp": "2023-01-01T12:00:00Z",
                        "pubdate": "2022-12-01T12:00:00Z",
                        "last_modified": "2023-02-01T10:30:00Z",
                        "path": "Author/Example Book",
                        "has_cover": True,
                        "uuid": "550e8400-e29b-41d4-a716-446655440000",
                    }
                ],
            }
        }
