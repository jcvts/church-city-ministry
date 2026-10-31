from dataclasses import dataclass
from typing import Literal
from uuid import UUID

UserRole = Literal["admin", "volunteer"]


@dataclass
class User:
    id: UUID
    username: str
    password_hash: str
    is_active: bool = True
    role: UserRole = "volunteer"
