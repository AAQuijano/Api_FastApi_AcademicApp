# Copilot Instructions for FastAPI Academic Management System

## Project Overview
This is a FastAPI + MySQL REST API for academic management (students, subjects, scores) with JWT-based role authorization (admin, professor, student). The codebase emphasizes clean separation via SQLModel ORM, factory pattern for app initialization, and comprehensive test coverage (>90% target).

## Architecture

### Core Application Factory Pattern
- **Entry point**: `app/main.py` imports and calls `create_app()` from `main_factory.py`
- **App factory**: `main_factory.py` creates the FastAPI instance with lifespan context manager for DB table creation
- **CORS middleware**: Configured to `["*"]` (change to specific domains in production)
- **Token endpoint**: `/token` uses `OAuth2PasswordRequestForm` for login; returns JWT with role embedded

### Database & ORM
- **Engine**: Configured in `app/db.py` with MySQL connection string from `.env`
- **Pool settings**: `pool_recycle=280` to handle inactive connection timeout (~5min)
- **Models**: SQLModel classes in `app/models.py` with automatic table creation via `metadata.create_all()` in lifespan
- **Tables**: `User`, `Role_User` (lookup), `Gender_User` (lookup), `Subject`, `Score`, `StudentSubjectLink` (junction), `Grade_Subject` (junction)
- **Relationships**: Defined bidirectionally (e.g., `User.role_ref` ↔ `Role_User.users`) using SQLModel's `Relationship`

### Authentication & Authorization
- **JWT tokens**: Created in `auth.py` with `sub` (username) and `user_id` claims; include role enum
- **Password hashing**: bcrypt via `passlib` with 12 rounds, defined once in `models.pwd_context`
- **Dependencies**:
  - `get_current_user()`: Validates token, returns `User` object; raises 401 if invalid
  - `get_current_admin_user()` / `get_current_professor_user()`: Role-specific versions
  - `require_role_or_none()`: Allows optional auth (returns `None` if no token or auth fails for specific roles)
- **Role validation**: Use `user.role` enum (not `user_id`) to check permissions; role must have matching `Role_User` entry

### Routers (API Endpoints)
- **Pattern**: Each entity (users, subjects, scores) has dedicated router in `app/routers/`
- **Dependency injection**: `Annotated[ModelType, Depends(function)]` throughout
- **Response models**: Use Pydantic schemas from `app/schemas.py` (e.g., `UserPublic` excludes sensitive fields)
- **Error handling**: Raise `HTTPException` with appropriate status code (401, 403, 404, 409, etc.)
- **Permission enforcement**: Check `current_user.role` in route logic; professors own only their subjects, students their enrollments

### Schemas (Validation & Response)
- **Base schemas**: `UserBase` contains shared fields; `User` is DB model; `UserCreate` is request payload
- **Field validators**: Use `@field_validator` with `ValidationInfo` context (e.g., require `specialization` only for professors)
- **Annotated constraints**: `CedulaStr = Annotated[str, StringConstraints(min_length=7, max_length=12)]`
- **Public views**: `UserPublic` removes `hashed_password`; convert via `convert_user_to_public()` helper

### Environment & Configuration
- **Settings**: Loaded in `app/config.py` via Pydantic `BaseSettings` from `.env`
- **Required vars**: `SECRET_KEY`, `DATABASE_URL` (must start with `mysql+pymysql://`, `postgresql://`, etc.), `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- **Validation**: Constructor raises `ValueError` if `SECRET_KEY` is missing or `DATABASE_URL` invalid

## Developer Workflows

### Setup & Local Development
```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
# Copy .env.example or create .env with DATABASE_URL=mysql+pymysql://user:pass@localhost/academicapp
uvicorn app.main_factory:create_app --reload --host 0.0.0.0 --port 8000
```

### Docker Compose (MySQL)
- Use `docker-compose.yml` to spin up MySQL container on port 3306
- DB credentials: user=`admin`, password=`Password#0*5`, database=`academicapp`
- Tables auto-created on app startup via lifespan handler

### Testing
```bash
pytest --cov=app --cov-report=html  # Generates coverage in htmlcov/
```
- **Fixtures**: `conftest.py` provides `test_app`, `db`, `test_student`, `test_professor`, `test_admin`, token fixtures
- **DB reset**: Each test uses fresh DB (created/dropped in fixture scope)
- **Suppress warnings**: SQLAlchemy warnings filtered in conftest via `filterwarnings`
- **Async tests**: Use `pytest-asyncio` for `async def test_*`; client fixture wraps app with `AsyncClient` and `ASGITransport`

### Debugging
- Request/response logging enabled by middleware in `main_factory.py` (print statements with `➡️` / `⬅️`)
- Enable SQL echo: `echo=True` in engine creation (shows all queries to console)
- Token claims: Decode JWT manually with `jwt.decode(token, secret, algorithms=['HS256'])` to inspect role

## Project-Specific Patterns & Conventions

### Role-Based Access Control
- Three roles: `Role.STUDENT`, `Role.PROFESSOR`, `Role.ADMIN` (defined as `Enum` in models)
- All routes requiring auth must import and use role-specific dependency or check `user.role` in handler
- **Permission pattern**: `current_user: professor_dep` in route signature auto-enforces professor role

### User Hierarchy
- **Students**: Enroll in subjects via `StudentSubjectLink`, receive `Score` records from professors
- **Professors**: Create subjects, own them (enforce via `professor_id` FK), assign scores
- **Admins**: Create/delete users, manage roles (user creation allows `require_role_or_none([Role.ADMIN])`)

### Field Defaults & Calculations
- `age` calculated from `birth_date` in route handler (not auto-computed in model); see `calculate_age()` in `users_routers.py`
- `specialization` required for professors, forbidden for others (enforced in `UserCreate.validate_specialization`)
- `career` required for students, forbidden for others (enforced in `UserCreate.validate_career`)

### Database Query Patterns
- **Single fetch**: `session.get(ModelClass, primary_key)`
- **List fetch**: `session.exec(select(ModelClass)).all()`
- **Conditional query**: `session.exec(select(ModelClass).where(condition)).first()`
- **Eager loading**: Use `.options(selectinload(Model.relationship_name))` to avoid N+1 queries
- **Uniqueness check**: Query with `(Model.field1 == value) | (Model.field2 == value)` for multiple fields

### Common Mistakes to Avoid
1. **Role mismatch**: Don't use `role_id` foreign key for permission checks; always use `user.role` enum
2. **Missing relationships**: Ensure `Relationship` is bidirectional when adding/removing from collections
3. **Unrefreshed entities**: After `commit()`, call `session.refresh(obj)` to sync with DB state before returning
4. **Incomplete schemas**: Request schemas (e.g., `UserCreate`) must include all required fields; use `Optional` only if nullable
5. **Auth dependency order**: `get_current_user` must be called before role-specific deps; ensure token is valid first

## Integration Points
- **Frontend**: Expects `/docs` (Swagger UI) and `/redoc` endpoints; CORS enabled for external clients
- **External DB**: Connect via `DATABASE_URL` env var; tested with MySQL 8.x and SQLite (for testing)
- **AWS deployment**: RDS MySQL for persistence; EC2 instance runs uvicorn; use HTTPS + Nginx in front

## Key Files Reference
| File | Purpose |
|------|---------|
| `app/main_factory.py` | App initialization with lifespan & middleware |
| `app/config.py` | Settings from `.env` |
| `app/models.py` | SQLModel definitions + bcrypt context |
| `app/schemas.py` | Pydantic validators & response models |
| `app/db.py` | Engine config + session dependency |
| `app/auth/auth.py` | JWT creation, user validation, role extraction |
| `app/auth/permissions.py` | Role-based dependency factories |
| `app/routers/` | Endpoint handlers (users, subjects, scores) |
| `tests/conftest.py` | Fixtures for test app, DB, users, tokens |
| `requirements.txt` | FastAPI, SQLModel, pytest, etc. |
