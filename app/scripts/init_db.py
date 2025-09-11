# scripts/init_db.py
from sqlmodel import Session, select
from app.db import engine
from app.models import Role_User, Gender_User, Role, Gender

def init_lookup_tables():
    """Inicializa las tablas de lookup con los valores de los enums"""
    with Session(engine) as session:
        print("🔄 Inicializando tablas de lookup...")
        
        # Inicializar ROLES
        roles_created = 0
        for role_enum in Role:
            # Verificar si ya existe
            existing = session.exec(
                select(Role_User).where(Role_User.role == role_enum)
            ).first()
            
            if not existing:
                new_role = Role_User(role=role_enum)
                session.add(new_role)
                roles_created += 1
                print(f"  ✅ Creando rol: {role_enum.value}")
        
        # Inicializar GÉNEROS
        genders_created = 0
        for gender_enum in Gender:
            # Verificar si ya existe
            existing = session.exec(
                select(Gender_User).where(Gender_User.gender == gender_enum)
            ).first()
            
            if not existing:
                new_gender = Gender_User(gender=gender_enum)
                session.add(new_gender)
                genders_created += 1
                print(f"  ✅ Creando género: {gender_enum.value}")
        
        # Guardar cambios
        session.commit()
        
        print(f"🎉 Tablas inicializadas:")
        print(f"   - Roles creados: {roles_created}")
        print(f"   - Géneros creados: {genders_created}")
        
        # Mostrar el contenido actual
        print("\n📊 Contenido actual de las tablas:")
        
        # Mostrar roles
        roles = session.exec(select(Role_User)).all()
        print("   Roles en la base de datos:")
        for role in roles:
            print(f"     {role.role_id}: {role.role.value}")
        
        # Mostrar géneros
        genders = session.exec(select(Gender_User)).all()
        print("   Géneros en la base de datos:")
        for gender in genders:
            print(f"     {gender.gender_id}: {gender.gender.value}")

def check_lookup_tables():
    """Verifica el estado de las tablas de lookup"""
    with Session(engine) as session:
        print("🔍 Verificando tablas de lookup...")
        
        # Contar registros
        role_count = session.exec(select(Role_User)).all()
        gender_count = session.exec(select(Gender_User)).all()
        
        print(f"   - Roles encontrados: {len(role_count)}")
        print(f"   - Géneros encontrados: {len(gender_count)}")
        
        return len(role_count) > 0 and len(gender_count) > 0

if __name__ == "__main__":
    # Ejecutar inicialización
    init_lookup_tables()
    
    # Verificar que todo esté correcto
    if check_lookup_tables():
        print("\n✅ ¡Inicialización completada exitosamente!")
    else:
        print("\n❌ Error en la inicialización")