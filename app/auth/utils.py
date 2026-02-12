#utils.py
from fastapi import HTTPException
from sqlmodel import Session, select
from app.models import Role, Gender
from app import models, schemas


def get_role_id(session: Session, rol: Role) -> int:
    """Convierte un enum Role a su ID correspondente en la base de datos"""
    rol_id  = session.exec(
        select(models.Role_User.role_id).where(models.Role_User.role == rol)
    ).first()

    if not rol_id:
        #Si no existe, créalo
        # role_record = models.Role_User(role = role)
        # session.add(role_record)
        # session.commit()
        # session.refresh(role_record)
        raise HTTPException(status_code=404, detail="Role no encontrado en la DB")
   
    return rol_id



def get_role_enum(session: Session, role_id: int) -> Role:
    role_enum = session.exec(
        select(models.Role_User). where(models.Role_User.role_id == role_id)
    ).first()

    if not role_enum:
        raise HTTPException(status_code=404, detail="Role no encontrado en la DB")
    
    return role_enum.role



def get_gender_id(session: Session, genero: Gender) -> int:
    """Convierte un enum Gender a su ID correspondente en la base de datos"""
    genero_id = session.exec(
        select(models.Gender_User.gender_id).where(models.Gender_User.gender == genero)
    ).first()

    if not genero_id:
        #Si no existe, créalo
        # gender_record = models.Gender_User(gender=gender)
        # session.add(gender_record)
        # session.commit()
        # session.refresh(gender_record)
        raise HTTPException(status_code=404, detail="Gender no encontrado en la DB")
    
    return genero_id


# def convert_user_to_public(user: models.User) -> schemas.UserPublic:
#     """
#     Convierte un modelo User a UserPublic con enums.
    
#     Requiere que las relaciones gender_ref y role_ref estén cargadas.
#     """
#     # Validar que tenemos los datos necesarios
#     if user.gender_ref is None:
#         raise ValueError(
#             f"gender_ref no está cargado para usuario {user.user_id}. "
#             "Usa: select(User).options(selectinload(User.gender_ref))"
#         )
    
#     if user.role_ref is None:
#         raise ValueError(
#             f"role_ref no está cargado para usuario {user.user_id}. "
#             "Usa: select(User).options(selectinload(User.role_ref))"
#         )
    
#     # Crear el diccionario de datos excluyendo IDs
#     data = user.model_dump(exclude={"gender_id", "role_id", "hashed_password"})
    
#     # Añadir los enums desde las relaciones
#     data.update({
#         "gender": user.gender_ref.gender,
#         "role": user.role_ref.role,
#     })
    
#     return schemas.UserPublic(**data)


def convert_user_to_public(user: models.User) -> schemas.UserPublic:
    """Convierte un modelo User a UserPublic con enums"""
    # Verificar que las relaciones están cargadas
    if user.gender_ref is None or user.role_ref is None:
        raise ValueError(
            f"Relaciones no cargadas para usuario {user.user_id}. "
            "Usa selectinload(User.gender_ref) y selectinload(User.role_ref) en tu consulta."
        )
    
    # Crear diccionario de datos
    user_data = user.model_dump(
        exclude={"gender_id", "role_id", "hashed_password", "gender_ref", "role_ref"},
        exclude_none=True
    )
    
    # Añadir enums desde las relaciones
    user_data.update({
        "gender": user.gender_ref.gender,
        "role": user.role_ref.role,
    })
    
    return schemas.UserPublic(**user_data)
