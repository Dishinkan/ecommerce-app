# app/routers/ristoranti.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import schemas, models
from app.database import get_db

router = APIRouter(
    prefix="/ristoranti",
    tags=["ristoranti"]
)

@router.post("/", response_model=schemas.Ristorante)
def create_ristorante(r: schemas.RistoranteCreate, db: Session = Depends(get_db)):
    db_obj = models.Ristorante(nome=r.nome, abbonamento_attivo=r.abbonamento_attivo)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

@router.get("/", response_model=List[schemas.Ristorante])
def read_ristoranti(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Ristorante).offset(skip).limit(limit).all()

@router.get("/{ristorante_id}", response_model=schemas.Ristorante)
def read_ristorante(ristorante_id: int, db: Session = Depends(get_db)):
    obj = db.query(models.Ristorante).get(ristorante_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Ristorante non trovato")
    return obj

@router.delete("/{ristorante_id}")
def delete_ristorante(ristorante_id: int, db: Session = Depends(get_db)):
    ristorante = db.query(models.Ristorante).get(ristorante_id)
    if not ristorante:
        raise HTTPException(status_code=404, detail="Ristorante non trovato")
    
    # Disattiva e scollega gli utenti associati
    utenti = db.query(models.User).filter(models.User.ristorante_id == ristorante_id).all()
    for u in utenti:
        u.is_active = False
        u.ristorante_id = None

    db.delete(ristorante)
    db.commit()
    return {"ok": True, "msg": f"Ristorante {ristorante_id} eliminato. {len(utenti)} utente/i disattivato/i"}
