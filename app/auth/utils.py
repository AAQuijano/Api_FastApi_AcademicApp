#utils.py
from fastapi import HTTPException
from sqlmodel import Session, select
from app.models import Role, Gender
from app import models


def get_role_id(session: Session, role: Role) -> int:
    """Convierte un enum Role a su ID correspondente en la base de datos"""
    role_record  = session.exec(
        select(models.Role_User). where(models.Role_User.role == role)
    ).first()

    if not role_record:
        #Si no existe, créalo
        # role_record = models.Role_User(role = role)
        # session.add(role_record)
        # session.commit()
        # session.refresh(role_record)
        raise HTTPException(status_code=404, detail="Role no encontrado en la DB")

    return role_record.role_id


def get_role_enum(session: Session, role_id: int) -> Role:
    role_enum = session.exec(
        select(models.Role_User). where(models.Role_User.role_id == role_id)
    ).first()

    if not role_enum:
        raise HTTPException(status_code=404, detail="Role no encontrado en la DB")
    
    return role_enum.role



def get_gender_id(session: Session, gender: Gender) -> int:
    """Convierte un enum Gender a su ID correspondente en la base de datos"""
    gender_record = session.exec(
        select(models.Gender_User). where(models.Gender_User == gender)
    ).first()

    if not gender_record:
        #Si no existe, créalo
        # gender_record = models.Gender_User(gender=gender)
        # session.add(gender_record)
        # session.commit()
        # session.refresh(gender_record)
        raise HTTPException(status_code=404, detail="Gender no encontrado en la DB")
    
    return gender_record.gender_id


    


