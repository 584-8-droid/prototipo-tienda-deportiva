from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./tienda.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
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

    # Relación simple y directa
    ofertante = relationship("User", backref="productos")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
