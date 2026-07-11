from fastapi import Header, HTTPException, status

from app.auth.models import CurrentUser, UserRole


def get_current_user(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    x_user_role: str = Header(default=UserRole.USER.value, alias="X-User-Role"),
) -> CurrentUser:
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication context",
        )

    try:
        user_id = int(x_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user id",
        ) from exc

    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user id",
        )

    try:
        role = UserRole(x_user_role)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user role",
        ) from exc

    return CurrentUser(
        user_id=user_id,
        role=role,
    )