
# src/material_scaleup/models/source.py

from pydantic import BaseModel

from datetime import date, datetime

__all__ = [
    "Source",
]

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
    """
    name: str
    publisher: str | None = None
    url: str | None = None
    publication_date: date | None = None
    accessed_at: datetime | None = None
