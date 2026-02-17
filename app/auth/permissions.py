# app/auth/permissions.py
from fastapi import Depends, HTTPException, Request
from typing import Optional,  Callable, List
from app.auth.auth import get_current_user
from app.auth.utils import get_role_enum
from app.models import Role, User
from fastapi.security.utils import get_authorization_scheme_param
from sqlmodel import Session
from app.db import get_db


def require_role_or_none(allowed_roles: List[Role]) -> Callable:
    async def dependency(request: Request, session: Session = Depends(get_db)) -> Optional[User]:
        auth = request.headers.get("Authorization")
        if not auth:
            return None  # No token → permitir como anónimo

        scheme, token = get_authorization_scheme_param(auth)
        if not token:
            return None

        try:
            user = await get_current_user(session, token)
        except Exception:
            return None

        if get_role_enum(session, user.role_id) not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="Permisos insuficientes"
            )

        return user

    return dependency
