from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import os

# Para Render usa PostgreSQL, localmente usa SQLite
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./tienda.db")

# Render usa postgres://, SQLAlchemy necesita postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id       = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email    = Column(String, unique=True, index=True)
    password = Column(String)
    role     = Column(String, default="user")

class Producto(Base):
    __tablename__ = "productos"
    id             = Column(Integer, primary_key=True, index=True)
    titulo         = Column(String(100), nullable=False)
    descripcion    = Column(Text, nullable=False)
    precio         = Column(Float, nullable=False)
    categoria      = Column(String(50), nullable=False)
    stock          = Column(Integer, default=0)
    imagen_url     = Column(String(200), nullable=True)
    estado         = Column(String(20), default="Pendiente")
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    ofertante_id   = Column(Integer, ForeignKey("users.id"), nullable=False)
    calificacion   = Column(Float, default=0.0)
    veces_solicitado = Column(Integer, default=0)
    ofertante      = relationship("User", backref="productos")

# ── NUEVO: Modelo Solicitud (Sprint 3) ────────────────────────────────────
class Solicitud(Base):
    __tablename__ = "solicitudes"
    id                 = Column(Integer, primary_key=True, index=True)
    producto_id        = Column(Integer, ForeignKey("productos.id"), nullable=False)
    nombre_demandante  = Column(String(100), nullable=False)
    email_demandante   = Column(String(120), nullable=False)
    telefono           = Column(String(20), nullable=True)
    mensaje            = Column(Text, nullable=True)
    estado             = Column(String(20), default="Pendiente")  # Pendiente/Aceptado/Rechazado
    fecha_solicitud    = Column(DateTime, default=datetime.utcnow)
    calificacion       = Column(Integer, nullable=True)
    comentario         = Column(String(200), nullable=True)
    producto           = relationship("Producto", backref="solicitudes")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
