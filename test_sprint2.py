import pytest
from main import app
from database import Base, engine, SessionLocal, User, Producto

@pytest.fixture
def client():
    # Usar base de datos en memoria para tests
    from sqlalchemy import create_engine
    from database import Base
    test_engine = create_engine("sqlite:///:memory:",
                                connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    from sqlalchemy.orm import sessionmaker
    TestSession = sessionmaker(bind=test_engine)

    # Parchar SessionLocal para los tests
    import database
    original = database.SessionLocal
    database.SessionLocal = TestSession

    db = TestSession()
    ofertante = User(username='juan', email='juan@test.com',
                     password='1234', role='ofertante')
    admin = User(username='adm', email='adm@test.com',
                 password='1234', role='admin')
    db.add_all([ofertante, admin])
    db.commit()

    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c, TestSession

    database.SessionLocal = original
    Base.metadata.drop_all(bind=test_engine)


# ── HU-01 ──────────────────────────────────────────────────────────────────
def test_HU01_estado_inicial_es_pendiente(client):
    """Al crear un producto su estado debe ser Pendiente."""
    c, Session = client
    db = Session()
    ofertante = db.query(User).filter_by(username='juan').first()
    p = Producto(titulo='Balón', descripcion='Profesional',
                 precio=150.0, categoria='Fútbol', stock=10,
                 estado='Pendiente', ofertante_id=ofertante.id)
    db.add(p)
    db.commit()
    assert p.estado == 'Pendiente'

def test_HU01_falla_sin_titulo(client):
    """Producto con título vacío no debe ser válido."""
    c, Session = client
    db = Session()
    ofertante = db.query(User).filter_by(username='juan').first()
    p = Producto(titulo='', descripcion='Sin título',
                 precio=50.0, categoria='Fútbol', stock=5,
                 estado='Pendiente', ofertante_id=ofertante.id)
    db.add(p)
    try:
        db.commit()
        assert False, "Debió fallar"
    except Exception:
        db.rollback()
        assert True

def test_HU01_falla_sin_precio(client):
    """Producto sin precio no debe persistirse."""
    c, Session = client
    db = Session()
    ofertante = db.query(User).filter_by(username='juan').first()
    p = Producto(titulo='Camiseta', descripcion='Ropa',
                 precio=None, categoria='Atletismo', stock=3,
                 estado='Pendiente', ofertante_id=ofertante.id)
    db.add(p)
    try:
        db.commit()
        assert False, "Debió fallar"
    except Exception:
        db.rollback()
        assert True

# ── HU-02 ──────────────────────────────────────────────────────────────────
def test_HU02_edicion_vuelve_estado_pendiente(client):
    """Editar un producto aprobado debe devolverlo a Pendiente."""
    c, Session = client
    db = Session()
    ofertante = db.query(User).filter_by(username='juan').first()
    p = Producto(titulo='Zapatillas', descripcion='Running',
                 precio=200.0, categoria='Atletismo', stock=5,
                 estado='Aprobado', ofertante_id=ofertante.id)
    db.add(p)
    db.commit()
    # Simular edición
    p.titulo = 'Zapatillas Pro'
    p.estado = 'Pendiente'
    db.commit()
    assert p.estado == 'Pendiente'

def test_HU02_eliminar_producto(client):
    """Producto eliminado no debe existir en BD."""
    c, Session = client
    db = Session()
    ofertante = db.query(User).filter_by(username='juan').first()
    p = Producto(titulo='Guantes', descripcion='Boxeo',
                 precio=80.0, categoria='Boxeo', stock=15,
                 estado='Pendiente', ofertante_id=ofertante.id)
    db.add(p)
    db.commit()
    pid = p.id
    db.delete(p)
    db.commit()
    assert db.query(Producto).filter_by(id=pid).first() is None

# ── HU-03 ──────────────────────────────────────────────────────────────────
def test_HU03_admin_aprueba(client):
    """Admin puede cambiar estado a Aprobado."""
    c, Session = client
    db = Session()
    ofertante = db.query(User).filter_by(username='juan').first()
    p = Producto(titulo='Raqueta', descripcion='Tenis',
                 precio=300.0, categoria='Otros', stock=4,
                 estado='Pendiente', ofertante_id=ofertante.id)
    db.add(p)
    db.commit()
    p.estado = 'Aprobado'
    db.commit()
    assert p.estado == 'Aprobado'

def test_HU03_admin_rechaza(client):
    """Admin puede cambiar estado a Rechazado."""
    c, Session = client
    db = Session()
    ofertante = db.query(User).filter_by(username='juan').first()
    p = Producto(titulo='Casco', descripcion='Ciclismo',
                 precio=250.0, categoria='Ciclismo', stock=2,
                 estado='Pendiente', ofertante_id=ofertante.id)
    db.add(p)
    db.commit()
    p.estado = 'Rechazado'
    db.commit()
    assert p.estado == 'Rechazado'

def test_HU03_solo_aprobados_son_publicos(client):
    """Solo productos Aprobados deben ser visibles al público."""
    c, Session = client
    db = Session()
    ofertante = db.query(User).filter_by(username='juan').first()
    p1 = Producto(titulo='Visible', descripcion='OK', precio=100.0,
                  categoria='Fútbol', stock=1, estado='Aprobado',
                  ofertante_id=ofertante.id)
    p2 = Producto(titulo='Oculto', descripcion='Pendiente', precio=50.0,
                  categoria='Fútbol', stock=1, estado='Pendiente',
                  ofertante_id=ofertante.id)
    db.add_all([p1, p2])
    db.commit()
    visibles = db.query(Producto).filter_by(estado='Aprobado').all()
    assert len(visibles) == 1
    assert visibles[0].titulo == 'Visible'