from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import datetime
import os

# SQLite database file path
DB_PATH = "sqlite:///./brand_guardian_v2.db"

engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class AuditRecord(Base):
    __tablename__ = "audit_records"

    id = Column(String, primary_key=True, index=True) # This will be our task_id
    video_url = Column(String, index=True)
    video_id = Column(String, nullable=True)
    status = Column(String, default="PENDING")
    region = Column(String, nullable=True) # Global, Europe, etc.
    final_status = Column(String, nullable=True) # PASS/FAIL
    final_report = Column(Text, nullable=True)
    compliance_results = Column(JSON, default=[])
    errors = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

# Create tables
def init_db():
    Base.metadata.create_all(bind=engine)

def get_db_context():
    db = SessionLocal()
    try:
        return db
    except:
        db.close()
        raise
