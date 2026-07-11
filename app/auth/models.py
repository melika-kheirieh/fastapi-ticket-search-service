from dataclasses import dataclass
from enum import StrEnum


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


@dataclass(frozen=True)
class CurrentUser:
    user_id: int
    role: UserRole

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN