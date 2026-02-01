from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


# Database Models
class SabbathSchool(Base):
    __tablename__ = "sabbath_school"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=False, index=True)  # Format: yy/ww (e.g., "26/04")
    data = Column(String, nullable=False)  # JSON stored as text


class WorshipService(Base):
    __tablename__ = "worship_service"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=False, index=True)  # Format: yy/ww (e.g., "26/04")
    data = Column(String, nullable=False)  # JSON stored as text


class YouthService(Base):
    __tablename__ = "youth_service"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=False, index=True)  # Format: yy/ww (e.g., "26/04")
    data = Column(String, nullable=False)  # JSON stored as text


class WednesdayService(Base):
    __tablename__ = "wednesday_service"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=False, index=True)  # Format: yy/ww (e.g., "26/04")
    data = Column(String, nullable=False)  # JSON stored as text


# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create all tables
def init_db():
    Base.metadata.create_all(bind=engine)
