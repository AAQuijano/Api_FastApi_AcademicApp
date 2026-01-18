#db.py
from sqlmodel import Session, create_engine, SQLModel
from .config import settings
from app import models
from contextvars import ContextVar
from typing import Generator, Optional, Union
from sqlalchemy.engine import Connection, Engine

# Tipos que puede aceptar Session
_SessionBind = Union[Engine, Connection, None]

# Engine principal
db_url = settings.DATABASE_URL
engine = create_engine(
    db_url,
    echo=True,
    pool_pre_ping=True,
    pool_recycle=280,  # importante si tu servidor cierra conexiones inactivas (~5min)
    pool_size=10,
    max_overflow=20,
    connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
)

# Engine de prueba (override)
engine_context: ContextVar[Optional[_SessionBind]] = ContextVar(
    "engine_context", 
    default=None
)


# Crear tablas (para uso directo si necesario)
def create_db_and_tables():
    models.SQLModel.metadata.create_all(engine)

# Sesión de base de datos
def get_db():
    engine_override = engine_context.get()
    db = Session(engine_override or engine)
    try:
        yield db
    finally:
        db.close()





