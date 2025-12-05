# app/routers/users.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app import schemas, models, utils
from app.database import get_db


router = APIRouter(
    prefix="/users",
    tags=["users"]
)

class ApprovePendingPayload(BaseModel):
    ristorante_id: Optional[int] = None  # ID ristorante scelto dal superuser
    nome_ristorante: Optional[str] = None  # solo se si vuole creare un nuovo ristorante
    ruoli: List[str] = []


# -------------------------
# Approva utente esistente / Superuser
# -------------------------
@router.put("/approve/{user_id}", response_model=schemas.User)
def approve_user(
    user_id: int,
    payload: schemas.ApprovePayload,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    # Ristorante: se fornito id esistente
    if payload.ristorante_id:
        r = db.query(models.Ristorante).get(payload.ristorante_id)
        if not r:
            raise HTTPException(status_code=404, detail="Ristorante non trovato")
        if r not in user.ristoranti:
            user.ristoranti.append(r)

    # Ristorante: se fornito nome nuovo
    elif payload.nome_ristorante:
        r = db.query(models.Ristorante).filter(models.Ristorante.nome == payload.nome_ristorante).first()
        if not r:
            r = models.Ristorante(nome=payload.nome_ristorante, abbonamento_attivo=True)
            db.add(r)
            db.commit()
            db.refresh(r)
        if r not in user.ristoranti:
            user.ristoranti.append(r)

    # Ruoli multipli
    if payload.ruoli:
        ruoli = db.query(models.Ruolo).filter(models.Ruolo.ruolo.in_(payload.ruoli)).all()
        for r in ruoli:
            if r not in user.ruoli:
                user.ruoli.append(r)

    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


# -------------------------
# Pending registrations
# -------------------------
@router.get("/pending")
def get_pending_users(db: Session = Depends(get_db)):
    pendings = db.query(models.RegistrazionePending).filter(models.RegistrazionePending.approvata == False).all()
    return [
        {
            "id": p.id,
            "email": p.email,
            "ruoli_richiesti": [r.ruolo for r in p.ruoli_richiesti],
            "ristorante_richiesto": p.ristorante_richiesto,
            "data_creazione": p.data_creazione.isoformat() if p.data_creazione else None
        }
        for p in pendings
    ]


# -------------------------
# Approva una registrazione pending
# -------------------------
@router.put("/pending/approve/{pending_id}", response_model=schemas.User)
def approve_pending_registration(
    pending_id: int,
    payload: ApprovePendingPayload,
    db: Session = Depends(get_db)
):
    pending = db.query(models.RegistrazionePending).get(pending_id)
    if not pending:
        raise HTTPException(status_code=404, detail="Registrazione non trovata")

    if db.query(models.User).filter(models.User.email == pending.email).first():
        raise HTTPException(status_code=400, detail="Esiste già un utente con questa email")

    # usa ristorante esistente o creane uno nuovo solo se "Altro"
    ristoranti = []
    if payload.ristorante_id:
        r = db.query(models.Ristorante).get(payload.ristorante_id)
        if not r:
            raise HTTPException(status_code=404, detail="Ristorante non trovato")
        ristoranti.append(r)
    elif payload.nome_ristorante:
        r = db.query(models.Ristorante).filter(models.Ristorante.nome == payload.nome_ristorante).first()
        if not r:
            r = models.Ristorante(nome=payload.nome_ristorante, abbonamento_attivo=True)
            db.add(r)
            db.commit()
            db.refresh(r)
        ristoranti.append(r)

    # crea l'utente attivo
    user = models.User(
        email=pending.email,
        hashed_password=pending.hashed_password,
        is_active=True
    )

    # assegna ristoranti multipli
    user.ristoranti = ristoranti

    # assegna ruoli multipli
    if payload.ruoli:
        ruoli = db.query(models.Ruolo).filter(models.Ruolo.ruolo.in_(payload.ruoli)).all()
        user.ruoli = ruoli

    db.add(user)
    pending.approvata = True
    db.commit()
    db.refresh(user)
    return user
