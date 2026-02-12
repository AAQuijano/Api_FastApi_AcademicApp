#scores_routers.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from app import models, schemas
from app.db import get_db
from app.auth.utils import get_role_enum

from app.auth.auth import get_current_user, get_current_professor_user
from typing import Annotated, List

router = APIRouter(prefix="/calificaciones", tags=["calificaciones"])

session_dep = Annotated[Session, Depends(get_db)]
professor_dep = Annotated[models.User, Depends(get_current_professor_user)]
user_dep = Annotated[models.User, Depends(get_current_user)]


@router.post("/", response_model=schemas.ScorePublic, status_code=status.HTTP_201_CREATED)
def create_score(score: schemas.ScoreCreate, session: session_dep, current_user: professor_dep):
    """Crear nueva calificación para un estudiante en una materia"""
    # Validar que la materia existe y pertenece al profesor
    subject = session.get(models.Subject, score.subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    
    if subject.professor_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes calificar en tus propias materias"
        )
    
    # Validar que el estudiante existe y está inscrito
    student = session.get(models.User, score.student_id)
    if not student or get_role_enum(session, student.role_id) != models.Role.STUDENT:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    # Verificar si el estudiante está inscrito en la materia
    existing_enrollment = session.exec(
        select(models.StudentSubjectLink).where(
            models.StudentSubjectLink.student_id == score.student_id,
            models.StudentSubjectLink.subject_id == score.subject_id
        )
    ).first()
    
    if not existing_enrollment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El estudiante no está inscrito en esta materia"
        )
    
    # Validar duplicado (mismo estudiante, materia y tipo de calificación)
    existing_score = session.exec(
        select(models.Score).where(
            models.Score.student_id == score.student_id,
            models.Score.subject_id == score.subject_id,
            models.Score.score_type == score.score_type
        )
    ).first()

    if existing_score:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una calificación de este tipo para el estudiante en esta materia"
        )
    
    if current_user.user_id is None:
        raise HTTPException(status_code=400, detail="Usuario no válido")

    # Crear la calificación
    db_score = models.Score(
        **score.model_dump(),
        professor_id=current_user.user_id
    )

    session.add(db_score)
    session.commit()
    session.refresh(db_score)
    return db_score


@router.get("/", response_model=List[schemas.ScorePublic])
def list_scores(session: session_dep, current_user: user_dep):
    """Listar todas las calificaciones (filtradas por rol)"""
    current_role = get_role_enum(session, current_user.role_id)
    
    if current_role == models.Role.PROFESSOR:
        # Profesores ven solo sus calificaciones
        scores = session.exec(
            select(models.Score).where(models.Score.professor_id == current_user.user_id)
        ).all()
    elif current_role == models.Role.STUDENT:
        # Estudiantes ven solo sus calificaciones
        scores = session.exec(
            select(models.Score).where(models.Score.student_id == current_user.user_id)
        ).all()
    else:
        # Admins ven todas
        scores = session.exec(select(models.Score)).all()
    
    return scores


@router.get("/{score_id}", response_model=schemas.ScorePublic)
def get_score(score_id: int, session: session_dep, current_user: user_dep):
    """Obtener una calificación específica"""
    score = session.get(models.Score, score_id)
    if not score:
        raise HTTPException(status_code=404, detail="Calificación no encontrada")

    current_role = get_role_enum(session, current_user.role_id)

    # Validar permiso
    if current_role == models.Role.PROFESSOR and score.professor_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver esta calificación")
    elif current_role == models.Role.STUDENT and score.student_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver esta calificación")
    
    return score


@router.patch("/{score_id}", response_model=schemas.ScorePublic)
def update_score(
    score_id: int,
    score_update: schemas.ScoreBase,
    session: session_dep,
    current_user: professor_dep
):
    """Actualizar una calificación (solo profesores pueden hacerlo)"""
    score = session.get(models.Score, score_id)
    if not score:
        raise HTTPException(status_code=404, detail="Calificación no encontrada")
    
    if score.professor_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes modificar calificaciones de otro profesor"
        )

    update_data = score_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(score, key, value)
    
    session.commit()
    session.refresh(score)
    return score


@router.delete("/{score_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_score(score_id: int, session: session_dep, current_user: professor_dep):
    """Eliminar una calificación (solo el profesor que la creó)"""
    score = session.get(models.Score, score_id)
    if not score:
        raise HTTPException(status_code=404, detail="Calificación no encontrada")
    
    if score.professor_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes eliminar calificaciones de otro profesor"
        )
    
    session.delete(score)
    session.commit()


@router.get("/por_estudiante/{student_id}", response_model=List[schemas.ScorePublic])
def scores_por_estudiante(
    student_id: int,
    session: session_dep,
    current_user: user_dep
):
    """Obtener todas las calificaciones de un estudiante"""
    # Validar que el estudiante existe
    student = session.get(models.User, student_id)
    if not student or get_role_enum(session, student.role_id) != models.Role.STUDENT:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    current_role = get_role_enum(session, current_user.role_id)
    
    # Validar permisos
    if current_role == models.Role.STUDENT and current_user.user_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes ver tus propias calificaciones"
        )
    
    scores = session.exec(
        select(models.Score).where(models.Score.student_id == student_id)
    ).all()
    
    return scores


@router.get("/por_materia/{subject_id}", response_model=List[schemas.ScorePublic])
def scores_por_materia(
    subject_id: int,
    session: session_dep,
    current_user: user_dep
):
    """Obtener todas las calificaciones de una materia"""
    # Validar que la materia existe
    subject = session.get(models.Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    
    current_role = get_role_enum(session, current_user.role_id)
    
    # Validar permisos
    if current_role == models.Role.PROFESSOR and subject.professor_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes ver calificaciones de tus propias materias"
        )
    
    scores = session.exec(
        select(models.Score).where(models.Score.subject_id == subject_id)
    ).all()
    
    return scores