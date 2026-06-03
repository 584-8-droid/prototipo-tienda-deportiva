import pytest
from main import app
from database import Base, engine, SessionLocal, User, Producto, Solicitud

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    ofertante = User(username="ofertante1", email="of@test.com",
                     password="1234", role="ofertante")
    db.add(ofertante)
    db.commit()
    producto = Producto(titulo="Balón de Fútbol", descripcion="Balón oficial",
                        precio=150.0, categoria="Fútbol",
                        estado="Aprobado", ofertante_id=ofertante.id)
    db.add(producto)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c

# ── SPEC 1: Búsqueda retorna página 200 con productos aprobados
def test_busqueda_retorna_productos(client):
    r = client.get('/buscar')
    assert r.status_code == 200
    assert 'Balón de Fútbol'.encode() in r.data

# ── SPEC 2: Filtro más recientes funciona
def test_filtro_recientes(client):
    r = client.get('/buscar?filtro=recientes')
    assert r.status_code == 200

# ── SPEC 3: Filtro mejor calificados funciona
def test_filtro_mejor_calificados(client):
    r = client.get('/buscar?filtro=mejor_calificados')
    assert r.status_code == 200

# ── SPEC 4: Búsqueda por texto encuentra producto
def test_busqueda_por_texto(client):
    r = client.get('/buscar?q=Balón')
    assert r.status_code == 200
    assert 'Balón'.encode() in r.data

# ── SPEC 5: Página de solicitud se muestra correctamente
def test_pagina_solicitar(client):
    r = client.get('/solicitar/1')
    assert r.status_code == 200
    assert 'Balón de Fútbol'.encode() in r.data

# ── SPEC 6: Solicitud válida se registra correctamente
def test_solicitud_valida(client):
    r = client.post('/solicitar/1', data={
        'nombre': 'Carlos Mamani',
        'email': 'carlos@test.com',
        'telefono': '70000001',
        'mensaje': 'Necesito 5 balones'
    }, follow_redirects=True)
    assert r.status_code == 200
    db = SessionLocal()
    s = db.query(Solicitud).first()
    assert s is not None
    assert s.nombre_demandante == 'Carlos Mamani'
    assert s.estado == 'Pendiente'
    db.close()

# ── SPEC 7: Solicitud sin email falla con error
def test_solicitud_sin_email(client):
    r = client.post('/solicitar/1', data={
        'nombre': 'Carlos', 'email': '', 'mensaje': 'test'
    })
    assert r.status_code == 200
    assert 'obligatorio'.encode() in r.data

# ── SPEC 8: Ofertante ve sus solicitudes
def test_ofertante_ve_solicitudes(client):
    client.set_cookie('user_role', 'ofertante')
    client.set_cookie('user_id', '1')
    r = client.get('/mis-solicitudes')
    assert r.status_code == 200

# ── SPEC 9: Ofertante puede aceptar solicitud
def test_aceptar_solicitud(client):
    # Crear solicitud primero
    client.post('/solicitar/1', data={
        'nombre': 'Ana', 'email': 'ana@test.com', 'mensaje': ''
    })
    client.set_cookie('user_role', 'ofertante')
    client.set_cookie('user_id', '1')
    r = client.post('/solicitudes/responder/1/aceptar', follow_redirects=True)
    assert r.status_code == 200
    db = SessionLocal()
    s = db.query(Solicitud).filter(Solicitud.id == 1).first()
    assert s.estado == 'Aceptado'
    db.close()

# ── SPEC 10: Ofertante puede rechazar solicitud
def test_rechazar_solicitud(client):
    client.post('/solicitar/1', data={
        'nombre': 'Luis', 'email': 'luis@test.com', 'mensaje': ''
    })
    client.set_cookie('user_role', 'ofertante')
    client.set_cookie('user_id', '1')
    r = client.post('/solicitudes/responder/1/rechazar', follow_redirects=True)
    assert r.status_code == 200
    db = SessionLocal()
    s = db.query(Solicitud).filter(Solicitud.id == 1).first()
    assert s.estado == 'Rechazado'
    db.close()