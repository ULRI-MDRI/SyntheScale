# src/material_scaleup/models/source.py

from datetime import date, datetime

from pydantic import BaseModel, Field

__all__ = [
    "Source",
    "SourceLocation",
]


class SourceLocation(BaseModel):
    """
    Location of supporting information within a source.

    Attributes:
        page (int | None):
            The page number within the source, if available.

        section (str | None):
            The section within the source, if available.

        table (str | None):
            The table within the source, if available.

        figure (str | None):
            The figure within the source, if available.

        excerpt (str | None):
            The excerpt within the source, if available.
    """

    page: int | None = Field(default=None, ge=1)
    section: str | None = None
    table: str | None = None
    figure: str | None = None
    excerpt: str | None = None


class Source(BaseModel):
    """
    Represents a source of information.

    Attributes:
        name (str):
            The name of the source.

        publisher (str | None):
            The publisher of the source, if available.

        url (str | None):
            The URL of the source, if available.

        publication_date (date | None):
            The publication date of the source, if available.

        accessed_at (datetime | None):
            The date and time when the source was accessed, if available.

        document_id (str | None):
            The document identifier of the source, if available.

        doi (str | None):
            The DOI of the source, if available.

        location (SourceLocation | None):
            The location of supporting information within the source,
            if available.
    """

    name: str
    publisher: str | None = None
    url: str | None = None
    publication_date: date | None = None
    accessed_at: datetime | None = None
    document_id: str | None = None
    doi: str | None = None
    location: SourceLocation | None = None
