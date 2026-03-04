# FastAPI + MySQL API - Sistema de Gestión Académica

Este proyecto es una API desarrollada con [FastAPI](https://fastapi.tiangolo.com/) conectada a una base de datos MySQL para la gestión académica de estudiantes, materias y calificaciones. ***El proyecto se encuentra en proceso de desarrollo y está destinado únicamente con fines educativos.***

---

## 🚀 Características

- Autenticación JWT con roles (Admin, Profesor, Estudiante)
- Gestión completa de usuarios (crear, leer, actualizar, eliminar)
- Gestión de materias con inscripciones de estudiantes
- Sistema de calificaciones por materia y estudiante
- Inscripción y desinscripción de estudiantes en materias
- Validaciones específicas por rol de usuario
- Documentación automática con Swagger UI y ReDoc
- Docker y docker-compose para entorno local

---

## ⚙️ Requisitos

- Python 3.10+
- MySQL 8.x
- pip / venv
- Docker y docker-compose (opcional)

---

## 📁 Estructura del Proyecto

```
app/
├── main.py                 # Punto de entrada
├── main_factory.py         # Fabricación de la app FastAPI
├── config.py               # Configuración y variables de entorno
├── db.py                   # Conexión a la base de datos
├── models.py               # Modelos SQLModel
├── schemas.py              # Esquemas Pydantic
├── auth/
│   ├── auth.py             # Autenticación JWT
│   ├── permissions.py      # Permisos por rol
│   └── utils.py            # Utilidades de autenticación
├── routers/
│   ├── users_routers.py    # Endpoints de usuarios
│   ├── subjects_routers.py # Endpoints de materias
│   └── scores_routers.py   # Endpoints de calificaciones
└── scripts/
    └── init_db.py          # Inicialización de la base de datos
```

---

## 🔐 Roles y Permisos

| Rol            | Permisos                                                                                                             |
|----------------|----------------------------------------------------------------------------------------------------------------------|
| **ADMIN**      | Crear/eliminar usuarios, ver todas las materias, ver/eliminar cualquier usuario                                      |
| **PROFESOR**   | Crear/actualizar/eliminar sus materias, inscribir/desinscribir estudiantes, gestionar calificaciones de sus materias |
| **ESTUDIANTE** | Ver sus materias, ver sus calificaciones, actualizar su propio perfil                                                |

---

## 📦 Instalación Local

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno en archivo .env
# DATABASE_URL=mysql+pymysql://{User}:{Password}@localhost:{port}/{db name}
# SECRET_KEY=tu_secret_key_aqui
# ALGORITHM=HS256
# ACCESS_TOKEN_EXPIRE_MINUTES=30

# Iniciar MySQL con Docker (opcional)
docker-compose up -d db
```

---

## 🚀 Ejecución

```bash
# Desarrollo (con auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Producción
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Accede a:
- http://localhost:8000/docs - Documentación Swagger UI
- http://localhost:8000/redoc - Documentación ReDoc
- http://localhost:8000/health - Endpoint de salud

---

## 📡 Endpoints de la API

### Autenticación
| Método | Endpoint | Descripción    | Auth |
|--------|----------|----------------|------|
| POST   | /token   | Iniciar sesión | No   |

### Usuarios (/usuarios)
| Método | Endpoint                | Descripción       | Auth | Rol           |
|--------|-------------------------|-------------------|------|---------------|
| POST   | /Create_user            | Crear usuario     | No   | Admin/anónimo |
| GET    | /Read_my_user           | Mi perfil         | Sí   | Cualquiera    |
| GET    | /read_user_id/{user_id} | Usuario por ID    | Sí   | Admin/propio  |
| PATCH  | /Update_user            | Actualizar perfil | Sí   | Cualquiera    |
| DELETE | /Delete_user/{user_id}  | Eliminar usuario  | Sí   | Admin         |
| GET    | /List_users             | Listar usuarios   | Sí   | Admin         |

### Materias (/materias)
| Método | Endpoint                                            | Descripción   | Auth | Rol      |
|--------|-----------------------------------------------------|---------------|------|----------|
| POST   | /Crear_cursos                                       | Crear materia | Sí   | Profesor |
| GET    | /Lista_de_cursos                                    | Listar todas  | Sí   | Admin    |
| GET    | /Mis_cursos                                         | Mis materias  | Sí   | Profesor |
| GET    | /{subject_id}/ver_curso                             | Ver materia   | Sí   | Admin    |
| PATCH  | /{subject_id}/Actualizar_curso                      | Actualizar    | Sí   | Profesor |
| DELETE | /{subject_id}/Borrar_curso                          | Eliminar      | Sí   | Profesor |
| GET    | /{subject_id}/Estudiantes_de_curso                  | Estudiantes   | Sí   | Profesor |
| POST   | /{subject_id}/{student_id}/Inscribir_estudiantes    | Inscribir     | Sí   | Profesor |
| DELETE | /{subject_id}/{student_id}/Desinscribir_estudiantes | Desinscribir  | Sí   | Profesor |

### Calificaciones (/calificaciones)
| Método | Endpoint                                        | Descripción                    | Auth | Rol                       |
|--------|-------------------------------------------------|--------------------------------|------|---------------------------|
| POST   | /Crear_nota                                     | Crear calificación             | Sí   | Profesor                  |
| GET    | /Ver_mis_notas/Estudiantes                      | Mis notas (estudiante)         | Sí   | Estudiante                | 
| GET    | /Ver_notas_por_estudiante/Profesor/{student_id} | Notas por estudiante           | Sí   | Profesor                  |
| GET    | /ver_notas_por_materia/Estudiante/{subject_id}  | Notas por materia (estudiante) | Sí   | Estudiante                |
| GET    | /Ver_nota_especifica/{score_id}                 | Ver nota específica            | Sí   | Admin/Profesor/Estudiante |
| PATCH  | /Actualizar_nota/{score_id}                     | Actualizar nota                | Sí   | Profesor                  |
| DELETE | /Borrar_nota/{score_id}                         | Eliminar nota                  | Sí   | Profesor                  |
| GET    | /Ver_nota_by_materia/Profesor/{subject_id}      | Notas por materia (profesor)   | Sí   | Profesor                  |

---

## ☁️ Despliegue en AWS EC2 + RDS

1. Crea una instancia EC2 (Ubuntu 22.04) y una base de datos MySQL en RDS.
2. Instala Python, venv y git en el servidor.
3. Clona este repositorio:

```bash
git clone https://github.com/AAQuijano/Api_FastApi_AcademicApp.git
cd Api_FastApi_Mysql
```

4. Configura entorno:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
nano .env  # Configura tus credenciales reales
```

5. Lanza el servidor:

```bash
# Puedes lanzar el server desde el comando uvicorn o crear un archivo .py que lance el server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 
python run.py 
```

---

## 🔐 Seguridad

- Nunca subas el archivo `.env` a GitHub.
- Usa HTTPS con Nginx o CloudFront en producción.
- Considera usar AWS Secrets Manager o SSM Parameter Store para almacenar claves.
- Configura CORS apropiadamente para producción (no usar `["*"]`).
