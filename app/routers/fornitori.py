# app/routers/fornitori.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import schemas, models
from app.database import get_db

router = APIRouter(
    prefix="/fornitori",
    tags=["fornitori"]
)

@router.post("/", response_model=schemas.Fornitore)
def create_fornitore(f: schemas.FornitoreCreate, db: Session = Depends(get_db)):
    db_obj = models.Fornitore(nome=f.nome, email=f.email)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

@router.get("/", response_model=List[schemas.Fornitore])
def read_fornitori(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Fornitore).offset(skip).limit(limit).all()

@router.get("/{fornitore_id}", response_model=schemas.Fornitore)
def read_fornitore(fornitore_id: int, db: Session = Depends(get_db)):
    obj = db.query(models.Fornitore).get(fornitore_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Fornitore non trovato")
    return obj
