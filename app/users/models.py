"""User domain models used for authentication."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class User:
    """Representation of an authenticated user session subject."""

    id: str
    email: Optional[str] = None
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login_at: datetime = field(default_factory=datetime.utcnow)

    def as_profile(self) -> dict[str, Optional[str]]:
        """Return a serialisable profile payload for API responses."""

        return {
            "id": self.id,
            "email": self.email,
            "telegram": {
                "id": self.telegram_id,
                "username": self.telegram_username,
            }
            if self.telegram_id
            else None,
            "roles": list(self.roles),
        }
