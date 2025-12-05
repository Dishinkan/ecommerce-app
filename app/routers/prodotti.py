# app/routers/prodotti.py

import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from app import schemas, models
from app.database import get_db
from app.dependencies import require_role
from app.config import UPLOADS_DIR

router = APIRouter(
    prefix="/prodotti",
    tags=["prodotti"]
)

# -----------------------------
# Helpers
# -----------------------------
def _save_image(file: Optional[UploadFile]) -> Optional[str]:
    if not file:
        return None
    # estensione sicura
    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower() if ext else ".jpg"
    name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(UPLOADS_DIR, name)
    with open(dest_path, "wb") as f:
        f.write(file.file.read())
    # URL statico servito da /static/uploads/...
    return f"/static/uploads/{name}"

# -----------------------------
# CRUD (protetto: window_dresser o superuser)
# -----------------------------
@router.post("/", response_model=schemas.Prodotto)
def create_prodotto(
    nome: str = Form(...),
    prezzo: float = Form(...),
    fornitore_id: int = Form(...),
    descrizione: Optional[str] = Form(None),
    immagine: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("window_dresser"))
):
    # immagine
    img_url = _save_image(immagine) if immagine else None

    nuovo = models.Prodotto(
        nome=nome,
        descrizione=descrizione,
        prezzo=prezzo,
        immagine_url=img_url,
        fornitore_id=fornitore_id
    )
    db.add(nuovo)
    db.commit()
    db.refresh(nuovo)
    return nuovo

@router.put("/{prodotto_id}", response_model=schemas.Prodotto)
def modifica_prodotto(
    prodotto_id: int,
    nome: str = Form(...),
    prezzo: float = Form(...),
    fornitore_id: int = Form(...),
    descrizione: Optional[str] = Form(None),
    immagine: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("window_dresser"))
):
    prodotto = db.query(models.Prodotto).get(prodotto_id)
    if not prodotto:
        raise HTTPException(status_code=404, detail="Prodotto non trovato")

    # aggiorna campi
    prodotto.nome = nome
    prodotto.prezzo = prezzo
    prodotto.fornitore_id = fornitore_id
    prodotto.descrizione = descrizione

    # se inviata una nuova immagine, salvala e sostituisci url
    if immagine and immagine.filename:
        img_url = _save_image(immagine)
        prodotto.immagine_url = img_url

    db.commit()
    db.refresh(prodotto)
    return prodotto

@router.delete("/{prodotto_id}", status_code=status.HTTP_204_NO_CONTENT)
def elimina_prodotto(
    prodotto_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("window_dresser"))
):
    prodotto = db.query(models.Prodotto).get(prodotto_id)
    if not prodotto:
        raise HTTPException(status_code=404, detail="Prodotto non trovato")
    db.delete(prodotto)
    db.commit()
    return

# -----------------------------
# Lettura
# -----------------------------
@router.get("/", response_model=List[schemas.Prodotto])
def read_prodotti(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Prodotto).offset(skip).limit(limit).all()

@router.get("/{prodotto_id}", response_model=schemas.Prodotto)
def read_prodotto(prodotto_id: int, db: Session = Depends(get_db)):
    obj = db.query(models.Prodotto).get(prodotto_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Prodotto non trovato")
    return obj

# -----------------------------
# Visibilità Prodotto <-> Ristoranti
# -----------------------------
@router.get("/{prodotto_id}/visibilita", response_model=List[int])
def get_visibility(
    prodotto_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("window_dresser"))
):
    prodotto = db.query(models.Prodotto).get(prodotto_id)
    if not prodotto:
        raise HTTPException(status_code=404, detail="Prodotto non trovato")
    return [r.id for r in prodotto.visibile_in]

@router.post("/{prodotto_id}/visibilita/{ristorante_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_visibility(
    prodotto_id: int,
    ristorante_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("window_dresser"))
):
    prodotto = db.query(models.Prodotto).get(prodotto_id)
    ristorante = db.query(models.Ristorante).get(ristorante_id)
    if not prodotto or not ristorante:
        raise HTTPException(status_code=404, detail="Prodotto o Ristorante non trovato")

    if ristorante not in prodotto.visibile_in:
        prodotto.visibile_in.append(ristorante)
        db.commit()
    return

@router.delete("/{prodotto_id}/visibilita/{ristorante_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_visibility(
    prodotto_id: int,
    ristorante_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("window_dresser"))
):
    prodotto = db.query(models.Prodotto).get(prodotto_id)
    ristorante = db.query(models.Ristorante).get(ristorante_id)
    if not prodotto or not ristorante:
        raise HTTPException(status_code=404, detail="Prodotto o Ristorante non trovato")

    if ristorante in prodotto.visibile_in:
        prodotto.visibile_in.remove(ristorante)
        db.commit()
    return
