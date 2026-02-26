# app/auth/permissions.py
from fastapi import Depends, HTTPException, Request, status
from typing import Optional,  Callable, List
from app.auth.auth import get_current_user
from app.auth.utils import get_role_enum
from app.models import Role, User
from fastapi.security.utils import get_authorization_scheme_param
from sqlmodel import Session
from app.db import get_db



async def get_optional_admin_or_anon(
    request: Request,
    session: Session = Depends(get_db)
) -> Optional[User]:
    """
    Dependencia que permite:
    - Usuarios anónimos (sin token)
    - Usuarios autenticados con rol ADMIN
    - Rechaza usuarios autenticados con otros roles
    """
    auth = request.headers.get("Authorization")
    
    # Caso 1: No hay token → anónimo permitido
    if not auth:
        return None
    
    # Extraer token
    scheme, token = get_authorization_scheme_param(auth)
    if not token:
        return None
    
    # Intentar obtener usuario
    try:
        user = await get_current_user(session, token)
        # Verificar rol
        user_role = get_role_enum(session, user.role_id)
        if user_role != Role.ADMIN:
            # Usuario autenticado pero no es admin → DENEGAR
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden crear usuarios"
            )
        
        # Es admin → permitir
        return user
    except Exception:
        return None  # Token inválido → tratar como anónimo
    
    


# def require_role_or_none(allowed_roles: List[Role]) -> Callable:
#     async def dependency(request: Request, session: Session = Depends(get_db)) -> Optional[User]:
#         auth = request.headers.get("Authorization")
#         if not auth:
#             return None  # No token → permitir como anónimo

#         scheme, token = get_authorization_scheme_param(auth)
#         if not token:
#             return None

#         try:
#             user = await get_current_user(session, token)
#         except Exception:
#             return None

#         if get_role_enum(session, user.role_id) not in allowed_roles:
#             raise HTTPException(
#                 status_code=403,
#                 detail="Permisos insuficientes"
#             )

#         return user

#     return dependency
