"""In-memory user repository for authentication flows."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Dict, Iterable, Optional

from .models import User


def _normalise_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    return email.strip().lower()


def _admin_emails() -> set[str]:
    raw = os.getenv("ADMIN_EMAILS", "")
    if not raw:
        return set()
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


class UserRepository:
    """Very small in-memory store used by the FastAPI app for auth."""

    def __init__(self) -> None:
        self._users_by_id: Dict[str, User] = {}
        self._users_by_email: Dict[str, User] = {}
        self._users_by_telegram: Dict[int, User] = {}

    def reset(self) -> None:
        """Remove all in-memory users (used in tests)."""

        self._users_by_id.clear()
        self._users_by_email.clear()
        self._users_by_telegram.clear()

    def all(self) -> Iterable[User]:  # pragma: no cover - convenience helper
        return self._users_by_id.values()

    def get(self, user_id: str) -> Optional[User]:
        return self._users_by_id.get(user_id)

    def upsert_google_user(self, email: str) -> User:
        email_key = _normalise_email(email)
        if not email_key:
            raise ValueError("Email is required for Google sign-in")

        user = self._users_by_email.get(email_key)
        if user is None:
            user = User(id=str(uuid.uuid4()), email=email_key)
            self._users_by_id[user.id] = user
            self._users_by_email[email_key] = user
        self._apply_roles(user)
        user.email = email_key
        user.last_login_at = datetime.utcnow()
        return user

    def upsert_telegram_user(
        self, telegram_id: int, username: Optional[str] = None, email: Optional[str] = None
    ) -> User:
        user = self._users_by_telegram.get(telegram_id)
        if user is None and email:
            email_key = _normalise_email(email)
            if email_key:
                user = self._users_by_email.get(email_key)
        if user is None:
            user = User(id=str(uuid.uuid4()), telegram_id=telegram_id)
            self._users_by_id[user.id] = user
            self._users_by_telegram[telegram_id] = user
        if user.telegram_id is None:
            user.telegram_id = telegram_id
        user.telegram_username = username or user.telegram_username
        if email:
            email_key = _normalise_email(email)
            if email_key:
                user.email = email_key
                self._users_by_email[email_key] = user
        self._apply_roles(user)
        user.last_login_at = datetime.utcnow()
        return user

    def _apply_roles(self, user: User) -> None:
        roles = set(user.roles)
        email = _normalise_email(user.email)
        if email and email in _admin_emails():
            roles.add("admin")
        user.roles = sorted(roles)
