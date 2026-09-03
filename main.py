from datetime import datetime
from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = "sqlite:///./dbt_companion.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Database Models ---
class DBLogEntry(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String)
    rating_before = Column(Integer, nullable=True)
    rating_after = Column(Integer, nullable=True)
    skill_practiced = Column(String, nullable=True)
    notes = Column(String, nullable=True)

class DBDiaryChecklist(Base):
    __tablename__ = "diary_card"
    id = Column(Integer, primary_key=True, index=True)
    week_suffix = Column(String, index=True)
    skill_name = Column(String)
    day_name = Column(String)
    completed = Column(Boolean, default=False)

Base.metadata.create_all(bind=engine)

# --- Pydantic Schemas ---
class LogEntryCreate(BaseModel):
    event_type: str
    rating_before: Optional[int] = None
    rating_after: Optional[int] = None
    skill_practiced: Optional[str] = None
    notes: Optional[str] = None

class LogEntryOut(LogEntryCreate):
    id: int
    timestamp: datetime
    class Config:
        orm_mode = True

class DiaryUpdate(BaseModel):
    week_suffix: str
    skill_name: str
    day_name: str
    completed: bool

# --- App Setup ---
app = FastAPI(title="DBT Companion API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Routes ---
@app.post("/api/logs", response_model=LogEntryOut)
def create_log(entry: LogEntryCreate, db: Session = Depends(get_db)):
    db_item = DBLogEntry(**entry.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/api/logs", response_model=List[LogEntryOut])
def get_logs(db: Session = Depends(get_db)):
    return db.query(DBLogEntry).order_by(DBLogEntry.timestamp.desc()).all()

@app.delete("/api/logs/{log_id}")
def delete_log(log_id: int, db: Session = Depends(get_db)):
    item = db.query(DBLogEntry).filter(DBLogEntry.id == log_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(item)
    db.commit()
    return {"ok": True}

@app.post("/api/diary/update")
def update_diary(entry: DiaryUpdate, db: Session = Depends(get_db)):
    record = db.query(DBDiaryChecklist).filter_by(
        week_suffix=entry.week_suffix,
        skill_name=entry.skill_name,
        day_name=entry.day_name
    ).first()
    if not record:
        record = DBDiaryChecklist(**entry.dict())
        db.add(record)
    else:
        record.completed = entry.completed
    db.commit()
    return {"status": "success"}