#user_routers.py
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, func, exists, and_
from app import models, schemas
from app.db import get_db
from app.auth.auth import get_current_user, get_current_admin_user
from app.auth.permissions import get_optional_admin_or_anon
from app.auth.utils import get_role_enum, get_gender_id, get_role_id, convert_user_to_public
from typing import Annotated, Optional
from sqlalchemy.orm import aliased

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


# Dependencias reutilizables
session_dep = Annotated[Session, Depends(get_db)]
user_dep = Annotated[models.User, Depends(get_current_user)]
admin_dep = Annotated[models.User, Depends(get_current_admin_user)]


def calculate_age(birth_date: Optional[date]) -> Optional[int]:
    if not birth_date:
        return None
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


@router.post("/", response_model=schemas.UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, 
                session: session_dep,
                 current_user: Optional[models.User] = Depends(get_optional_admin_or_anon)
                 ):
    
    # print("🔍 Rol recibido:", user.role)
    # print("🔍 Especialización recibida:", user.specialization)
    # print("🔍 Current user:", current_user)
    # if current_user is not None and get_role_enum(session, current_user.role_id) != models.Role.ADMIN:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Solo un administrador puede crear nuevos usuarios estando autenticado"
    #     )
    try:
        # Verificar unicidad
        existing_user = session.exec(
            select(models.User).where(
                (models.User.email == user.email) |
                (models.User.name_user == user.name_user) |
                (models.User.cedula == user.cedula)
            )
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El email, nombre de usuario o cédula ya están registrados"
            )
        
        # Validar especialización si es profesor
        # if user.role == models.Role.PROFESSOR and not user.specialization:
        #     raise HTTPException(
        #         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        #         detail="Especialización requerida para profesores"
        #     )
        
        if user.role != models.Role.PROFESSOR and user.specialization not in (None,""):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Solo los profesores pueden tener especialización"
            )
        
        if user.role != models.Role.STUDENT and user.career not in (None,""):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Solo los estudiantes pueden tener carrera"
            )
        
        # if user.role == models.Role.STUDENT and not user.career:
        #     raise HTTPException(
        #         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        #         detail="Carrera requerida para estudiantes"
        #     )

        #Convertir enums en ID
        role_id = get_role_id(session, user.role)
        gender_id = get_gender_id(session, user.gender)


        hashed_password = models.pwd_context.hash(user.password)
        age = calculate_age(user.birth_date)

        db_user = models.User(
            **user.model_dump(exclude={"password", "role", "gender"}),
            hashed_password=hashed_password,
            age=age,
            role_id=role_id,
            gender_id=gender_id
        )
        session.add(db_user)
        session.commit()
        session.refresh(db_user)

        return convert_user_to_public(db_user)

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear usuario: {str(e)}"
        ) from e


@router.get("/me", response_model=schemas.UserPublic)
async def read_users_me(current_user: user_dep):
    return convert_user_to_public(current_user)


@router.get("/{user_id}", response_model=schemas.UserPublic)
async def read_user(user_id: int, session: session_dep, current_user: user_dep):
    if get_role_enum(session, current_user.role_id) != models.Role.ADMIN and current_user.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver este usuario"
        )
    user = session.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return convert_user_to_public(user)


@router.patch("/Update user", response_model=schemas.UserPublic)
async def update_my_user(
    user_update: schemas.UserUpdate,
    session: session_dep,
    current_user: user_dep
):
    
    user = session.get(models.User, current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    update_data = user_update.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if v is not None}

    user_role = get_role_enum(session, user.role_id)

    # 🔍 DEBUG: Imprime el rol del usuario
    # print(f"🔍 User ID: {user.user_id}")
    # print(f"🔍 Role ID: {user.role_id}")
    # print(f"🔍 Role Enum: {user_role}")
    # print(f"🔍 Role Type: {type(user_role)}")
    # print(f"🔍 Is Professor? {user_role == models.Role.PROFESSOR}")

    # Validaciones manuales porque 'role' no viene en PATCH
    if "specialization" in update_data and user_role != models.Role.PROFESSOR:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Solo los profesores pueden tener especialización"
        )
    if "career" in update_data and user_role != models.Role.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Solo los estudiantes pueden tener carrera"
        )
    
    if "birth_date" in update_data:
        update_data["age"] = calculate_age(update_data["birth_date"])


    if 'password' in update_data:
        update_data['hashed_password'] = models.pwd_context.hash(update_data.pop('password'))

    for key, value in update_data.items():
        setattr(user, key, value)

    session.commit()
    session.refresh(user)
    return convert_user_to_public(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, session: session_dep, current_user: admin_dep):
    user = session.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    session.delete(user)
    session.commit()
    return None


@router.get("/", response_model=list[schemas.UserPublic])
async def list_users(
    session: session_dep,
    current_user: admin_dep,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100)
):
    users = session.exec(
        select(models.User).order_by(models.User.name_user).offset(skip).limit(limit)
    ).all()
    return [convert_user_to_public(u) for u in users]


# @router.get("/{user_id}/historial", response_model=list[schemas.SubjectHistory])
# def obtener_historial_academico(user_id: int, session: session_dep, current_user: user_dep):
#     current_user_role = get_role_enum(session, current_user.role_id)
#     allowed_roles = [models.Role.ADMIN, models.Role.PROFESSOR]
    
#     if current_user_role not in allowed_roles:
#         raise HTTPException(
#             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#             detail="No tienes permiso para ver historial"
#         )
    
#     # Verificar que el usuario existe y es estudiante
#     user = session.get(models.User, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
#     # Verificar que es estudiante
#     user_role = get_role_enum(session, user.role_id)
#     if user_role != models.Role.STUDENT:
#         raise HTTPException(
#             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#             detail="El historial académico solo está disponible para estudiantes"
#         )
    
#     # Usar alias para evitar conflicto de nombres
#     Subject = aliased(models.Subject)
    
#     if current_user_role == models.Role.PROFESSOR:
#         # Profesores: solo pueden ver notas de sus materias
#         resultados = session.exec(
#             select(
#                 Subject.name_subject,
#                 models.Score.valor
#             )
#             .join(models.Score, models.Score.subject_id == Subject.subject_id)  # 🔧 CORREGIDO
#             .where(and_(
#                 models.Score.student_id == user_id,
#                 Subject.professor_id == current_user.user_id  # ← FILTRO IMPORTANTE
#             ))
#             .order_by(Subject.name_subject)
#         ).all()
#     else:
#         # Admin: puede ver todas las notas
#         resultados = session.exec(
#             select(
#                 Subject.name_subject,
#                 models.Score.valor
#             )
#             .join(models.Score, models.Score.subject_id == Subject.subject_id)  # 🔧 CORREGIDO
#             .where(models.Score.student_id == user_id)
#             .order_by(Subject.name_subject)
#         ).all()

#     # Si no hay notas, devolver lista vacía
#     if not resultados:
#         return []
    
#     # Construir historial
#     historial = {}
#     for materia_nombre, valor in resultados:
#         historial.setdefault(materia_nombre, []).append(valor)

#     from statistics import mean
#     return [
#         schemas.SubjectHistory(
#             materia=materia,
#             notas=notas,
#             promedio=round(mean(notas), 2) if notas else 0
#         )
#         for materia, notas in historial.items()
#     ]
# @router.get("/{user_id}/historial", response_model=list[schemas.SubjectHistory])
# def obtener_historial_academico(user_id: int, session: session_dep, current_user: user_dep):
#     current_user_role = get_role_enum(session, current_user.role_id)
#     allowed_roles = [models.Role.ADMIN,models.Role.PROFESSOR]
#     if current_user_role not in allowed_roles :
#         raise HTTPException(
#             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#             detail="No tienes permiso para ver historial"
#         )
    
#     # Verificar que el usuario existe y es estudiante
#     user = session.get(models.User, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
#     #verificar que es estudiante
#     user_role = get_role_enum(session, user.role_id)
#     if user_role != models.Role.STUDENT:
#         raise HTTPException(
#             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#             detail="El historial académico solo está disponible para estudiantes"
#             )
#     # Usar alias para evitar conflicto de nombres
#     Subject = aliased(models.Subject)
#     if current_user_role == models.Role.PROFESSOR:
#         #Profesores: solo pueden ver notas de sus materias
#         resultados = session.exec(
#             select(
#                 Subject.name_subject,
#                 models.Score.valor
#             )
#             .join(models.Score, models.Score.subject_id == Subject.subject_id)
#             .where(and_(
#                 models.Score.student_id == user_id,
#                 Subject.professor_id == current_user.user_id  # ← ¡FILTRO IMPORTANTE!
#             ))
#             .order_by(Subject.name_subject)
#         ).all()

#     else: 
#         #Admin: puede ver todas las notas
#         resultados = session.exec(
#             select(
#                 Subject.name_subject,
#                 models.Score.valor
#             )
#             .join(models.Score, models.Score.subject_id == Subject.subject_id)
#             .where(models.Score.student_id == user_id)
#             .order_by(Subject.name_subject)
#         ).all() 

#     # Si no hay notas, devolver lista vacía
#     if not resultados:
#         return []
    

#     # Construir historial
#     historial = {}
#     for materia_nombre, valor in resultados:
#         historial.setdefault(materia_nombre, []).append(valor)

#     from statistics import mean
#     return [
#         schemas.SubjectHistory(
#             materia=materia,
#             notas=notas,
#             promedio=round(mean(notas), 2) if notas else 0
#         )
#         for materia, notas in historial.items()
#     ]


# @router.patch("/{user_id}", response_model=schemas.UserPublic)
# async def update_users(
#     user_id: int,
#     user_update: schemas.UserUpdate,
#     session: session_dep,
#     current_user: user_dep
# ):
#     current_user_role = get_role_enum(session, current_user.role_id)
#     #Actualizar endpoint
#     if current_user_role != models.Role.ADMIN and user_id != current_user.user_id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Solo puedes modificar tu propio perfil"
#         )

#     user = session.get(models.User, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="Usuario no encontrado")

#     update_data = user_update.model_dump(exclude_unset=True)
#     update_data = {k: v for k, v in update_data.items() if v is not None}

#     user_role = get_role_enum(session, user.role_id)

#     # Validaciones manuales porque 'role' no viene en PATCH
#     if "specialization" in update_data and user_role != models.Role.PROFESSOR:
#         raise HTTPException(
#             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#             detail="Solo los profesores pueden tener especialización"
#         )
#     if "career" in update_data and user_role != models.Role.STUDENT:
#         raise HTTPException(
#             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#             detail="Solo los estudiantes pueden tener carrera"
#         )
    
#     if "birth_date" in update_data:
#         update_data["age"] = calculate_age(update_data["birth_date"])


#     if 'password' in update_data:
#         update_data['hashed_password'] = models.pwd_context.hash(update_data.pop('password'))

#     for key, value in update_data.items():
#         setattr(user, key, value)

#     session.commit()
#     session.refresh(user)
#     return convert_user_to_public(user)