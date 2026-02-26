#subjects_routers.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, col
from sqlalchemy.orm import selectinload
from app import models, schemas
from app.db import get_db
from app.auth.auth import get_current_user, get_current_professor_user, get_current_admin_user
from app.auth.utils import convert_user_to_public, get_role_enum
from typing import Annotated

router = APIRouter(prefix="/materias", tags=["materias"])

session_dep = Annotated[Session, Depends(get_db)]
professor_dep = Annotated[models.User, Depends(get_current_professor_user)]
admin_dep = Annotated[models.User, Depends(get_current_admin_user)]
user_dep = Annotated[models.User, Depends(get_current_user)]


@router.post("/Crear_cursos", response_model=schemas.SubjectPublic, status_code=status.HTTP_201_CREATED)
def create_subject(subject: schemas.SubjectCreate, session: session_dep, current_user: professor_dep):

    if current_user.user_id is None:
        raise HTTPException(status_code=400, detail="Usuario no válido")
    
    db_subject = models.Subject(
        **subject.model_dump(),
        professor_id=current_user.user_id)
    session.add(db_subject)
    session.commit()
    session.refresh(db_subject)
    return db_subject


@router.get("/Lista_de_cursos", response_model=list[schemas.SubjectPublic])
def list_subjects(session: session_dep, current_user: user_dep):
    user_role = get_role_enum(session, current_user.role_id)
    if user_role != models.Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden ver materias"
        )
    subjects = session.exec(select(models.Subject)).all()
        
    return subjects


@router.get("/Mis_cursos", response_model = list[schemas.SubjectPublic])
def my_subjects(session: session_dep, current_user: professor_dep):
    subjects = session.exec(select(models.Subject)
                            .where(models.Subject.professor_id == current_user.user_id)
                            .order_by(models.Subject.name_subject)
                            ).all()
    return subjects


@router.get("/{subject_id}/ver_curso", response_model=schemas.SubjectPublic)
def get_subject(subject_id: int, session: session_dep, current_user: user_dep):
    user_role = get_role_enum(session, current_user.role_id)
    if user_role != models.Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden ver materias"
        )
    subject = session.get(models.Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    return subject


@router.patch("/{subject_id}/Actualizar_curso", response_model=schemas.SubjectPublic)
def update_subject(subject_id: int, subject_update: schemas.SubjectCreate, session: session_dep, current_user: professor_dep):
    db_subject = session.get(models.Subject, subject_id)
    if not db_subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    if db_subject.professor_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Solo puedes modificar tus propias materias")

    update_data = subject_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_subject, key, value)

    session.commit()
    session.refresh(db_subject)
    return db_subject


@router.delete("/{subject_id}/Borrar_curso", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(subject_id: int, session: session_dep, current_user: professor_dep):
    subject = session.get(models.Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    if subject.professor_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Solo puedes eliminar tus propias materias")
    session.delete(subject)
    session.commit()
    return None


@router.get("/{subject_id}/Estudiantes_de_curso", response_model=list[schemas.UserPublic])
def list_subject_students(subject_id: int, session: session_dep, current_user: user_dep):
    subject = session.get(models.Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    
    # Verificar permisos (opcional, según tu lógica)
    current_role = get_role_enum(session, current_user.role_id)
    if current_role == models.Role.PROFESSOR and subject.professor_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes ver estudiantes de tus propias materias"
        )
    
    # Cargar estudiantes con sus relaciones para la conversión
    subject_with_students = session.exec(
        select(models.User)
        .join(models.StudentSubjectLink)
        .where(models.StudentSubjectLink.subject_id == subject_id)
        .where(models.StudentSubjectLink.student_id == models.User.user_id)
    ).all()

    print(subject_with_students)
    return [convert_user_to_public(student) for student in subject_with_students]
    #return subject_with_students

# @router.get("/{subject_id}/estudiantes", response_model=list[schemas.UserPublic])
# def list_subject_students(subject_id: int, session: session_dep, current_user: user_dep):
#     # Primero verificamos que la materia existe
#     subject = session.get(models.Subject, subject_id)
#     if not subject:
#         raise HTTPException(status_code=404, detail="Materia no encontrada")
    
#     # Luego cargamos los estudiantes usando selectinload (NO selectload)
#     statement = (
#         select(models.Subject)
#         .where(models.Subject.subject_id == subject_id)
#         .options(selectinload(models.Subject.students))  # Sin paréntesis
#     )
    
#     subject_with_students = session.exec(statement).first()
    
#     # Verificamos que no sea None antes de acceder a sus atributos
#     if not subject_with_students:
#         raise HTTPException(status_code=404, detail="Materia no encontrada")
    
#     # Ahora sí podemos acceder a students de forma segura
#     if not subject_with_students.students:
#         return []  # Retornar lista vacía si no hay estudiantes
    
#     return [convert_user_to_public(student) for student in subject_with_students.students]


@router.post("/{subject_id}/inscribir_estudiantes", status_code=status.HTTP_200_OK)
def enroll_student(subject_id: int, student_id: int, session: session_dep, current_user: professor_dep):
    subject = session.get(models.Subject, subject_id)
    student = session.get(models.User, student_id)
    
    if not subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    
    if not student:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    
    if subject.professor_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Solo puedes inscribir estudiantes en tus propias materias")
    
    # Verificar si ya está inscrito
    existing_link = session.exec(
        select(models.StudentSubjectLink).where(
            models.StudentSubjectLink.student_id == student_id,
            models.StudentSubjectLink.subject_id == subject_id
        )
    ).first()
    
    if existing_link:
        raise HTTPException(status_code=409, detail="El estudiante ya está inscrito en esta materia")
    
    # Crear la relación
    new_link = models.StudentSubjectLink(
        student_id=student_id,
        subject_id=subject_id
    )
    session.add(new_link)
    session.commit()
    
    # Verificar si ya está inscrito
    existing_link = session.exec(
        select(models.StudentSubjectLink).where(
            models.StudentSubjectLink.student_id == student_id,
            models.StudentSubjectLink.subject_id == subject_id
        )
    ).first()

    return {"message": "Estudiante inscrito exitosamente"}


@router.delete("/{subject_id}/desinscribir_estudiantes/{student_id}", status_code=status.HTTP_200_OK)
def unenroll_student(subject_id: int, student_id: int, session: session_dep, current_user: professor_dep):
    subject = session.get(models.Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    
    if subject.professor_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Solo puedes desinscribir estudiantes de tus propias materias")
    
    # Buscar y eliminar la relación
    link = session.exec(
        select(models.StudentSubjectLink).where(
            models.StudentSubjectLink.student_id == student_id,
            models.StudentSubjectLink.subject_id == subject_id
        )
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Estudiante no inscrito en esta materia")
    
    session.delete(link)
    session.commit()
    return {"message":"Estudiante desenscrito correctamente"}
