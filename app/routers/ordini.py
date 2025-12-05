# app/routers/ordini.py

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime, time

import logging

logger = logging.getLogger(__name__)

from app import models, schemas
from app.database import get_db

router = APIRouter(
    prefix="/ordini",
    tags=["ordini"]
)

# --- Recupera ordine aggregato corrente ---
@router.get("/order_manager/order_aggregato")
def get_ordine_aggregato(request: Request, ristorante_id: int = None, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(403, "Utente non autenticato")

    user = db.query(models.User).get(user_id)
    if not user:
        raise HTTPException(404, "Utente non valido")

    # Se non è passato il ristorante_id, prova a prendere il primo associato
    if ristorante_id is None:
        if not user.ristoranti:
            raise HTTPException(404, "Nessun ristorante associato all'utente")
        ristorante_id = user.ristoranti[0].id

    ordine_agg = agglomera_ordini(db, user.id, ristorante_id)
    if not ordine_agg:
        return JSONResponse({"righe": [], "totale": 0})

    # Trasforma in JSON serializzabile
    result = {
        "id": ordine_agg.id,
        "totale": ordine_agg.totale,
        "righe": [
            {
                "prodotto_id": getattr(r, "prodotto_id", (r.prodotto.id if r.prodotto else None)),
                "prodotto": {"id": r.prodotto.id, "nome": r.prodotto.nome} if r.prodotto else None,
                "quantita": r.quantita,
                "prezzo_unitario": r.prezzo_unitario
            } for r in ordine_agg.righe
        ]
    }
    return JSONResponse(jsonable_encoder(result))

# --- Modifica righe ordine esistente ---
class AggiornaRigaOrdine(schemas.BaseModel):
    prodotto_id: int
    quantita: float

@router.put("/order_manager/order_aggregato", response_model=schemas.Ordine)
def aggiorna_ordine_aggregato(
    righe: List[AggiornaRigaOrdine],
    request: Request,
    db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(403, "Utente non autenticato")

    ordine = (
        db.query(models.Ordine)
        .options(joinedload(models.Ordine.righe).joinedload(models.OrderItem.prodotto))
        .filter(models.Ordine.user_id == user_id, models.Ordine.inviato == False)
        .order_by(models.Ordine.data_ordine.desc())
        .first()
    )
    if not ordine:
        raise HTTPException(404, "Nessun ordine aggregato trovato")
    
    righe_dict = {r.prodotto_id: r for r in ordine.righe}
    totale = 0.0

    for r in righe:
        if r.prodotto_id in righe_dict:
            if r.quantita > 0:
                righe_dict[r.prodotto_id].quantita = r.quantita
                totale += r.quantita * righe_dict[r.prodotto_id].prezzo_unitario
            else:
                db.delete(righe_dict[r.prodotto_id])
        else:
            if r.quantita > 0:
                prod = db.query(models.Prodotto).get(r.prodotto_id)
                if not prod:
                    continue
                item = models.OrderItem(
                    ordine_id=ordine.id,
                    prodotto_id=prod.id,
                    quantita=r.quantita,
                    prezzo_unitario=prod.prezzo
                )
                db.add(item)
                totale += r.quantita * prod.prezzo

    ordine.totale = totale
    db.commit()
    db.refresh(ordine)
    return ordine

# --- Funzione di agglomerazione ordini ---
def agglomera_ordini(db: Session, user_id: int, ristorante_id: int):
    ordini = (
        db.query(models.Ordine)
        .options(joinedload(models.Ordine.righe))
        .filter(
            models.Ordine.user_id == user_id,
            models.Ordine.ristorante_id == ristorante_id,
            models.Ordine.inviato == False
        )
        .all()
    )
    
    if not ordini:
        return None
    
    ordine_agg = models.Ordine(
        user_id=user_id,
        ristorante_id=ristorante_id,
        data_ordine=datetime.utcnow(),
        note="Ordine aggregato del giorno",
        totale=0.0,
        inviato=False
    )
    db.add(ordine_agg)
    db.flush()

    totale = 0.0
    righe_dict = {}

    for ordine in ordini:
        for r in ordine.righe:
            if r.prodotto_id in righe_dict:
                righe_dict[r.prodotto_id]['quantita'] += r.quantita
            else:
                righe_dict[r.prodotto_id] = {
                    'prodotto_id': r.prodotto_id,
                    'quantita': r.quantita,
                    'prezzo_unitario': r.prezzo_unitario
                }
        db.delete(ordine)

    for r in righe_dict.values():
        if r['quantita'] > 0:
            item = models.OrderItem(
                ordine_id=ordine_agg.id,
                prodotto_id=r['prodotto_id'],
                quantita=r['quantita'],
                prezzo_unitario=r['prezzo_unitario']
            )
            totale += r['quantita'] * r['prezzo_unitario']
            db.add(item)

    ordine_agg.totale = totale
    db.commit()
    db.refresh(ordine_agg)

    # --- PULIZIA AUTOMATICA: cancella righe senza ordine_id ---
    db.query(models.OrderItem).filter(models.OrderItem.ordine_id == None).delete(synchronize_session=False)
    db.commit()

    if totale <= 0 or not ordine_agg.righe:
        db.delete(ordine_agg)
        db.commit()
        return None

    return ordine_agg

# --- Creazione ordine ---
@router.post("/", response_model=schemas.Ordine)
def create_ordine(
    o: schemas.OrdineCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    now = datetime.now().time()
    if now >= time(15, 30):
        raise HTTPException(403, "Gli ordini possono essere modificati solo fino alle 15:30.")
        
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(403, "Utente non autenticato")

    user = db.query(models.User).get(user_id)

    # ⚠️ PRENDI ristorante_id DAL PAYLOAD invece che dall'utente
    if not o.ristorante_id:
        raise HTTPException(400, "Devi specificare un ristorante")
    
    ristorante = db.query(models.Ristorante).get(o.ristorante_id)
    if not ristorante or ristorante not in user.ristoranti:
        raise HTTPException(403, "Non sei associato a questo ristorante")

    ordine_temp = models.Ordine(
        user_id=user.id,
        ristorante_id=ristorante.id,
        data_ordine=datetime.utcnow(),
        note=o.note
    )
    db.add(ordine_temp)
    db.flush()

    totale = 0.0
    for r in o.righe:
        prod = db.query(models.Prodotto).get(r.prodotto_id)
        if not prod:
            raise HTTPException(404, f"Prodotto {r.prodotto_id} non trovato")
        item = models.OrderItem(
            ordine_id=ordine_temp.id,
            prodotto_id=r.prodotto_id,
            quantita=r.quantita,
            prezzo_unitario=prod.prezzo
        )
        totale += r.quantita * prod.prezzo
        db.add(item)

    ordine_temp.totale = totale
    db.commit()
    db.refresh(ordine_temp)

    # ⚠️ PRENDI ristorante_id DAL PAYLOAD invece che dall'utente
    ordine_agg = agglomera_ordini(db, user.id, o.ristorante_id)
    if not ordine_agg:
        raise HTTPException(400, "L'ordine risultante è vuoto dopo la variazione dei prodotti.")

    return ordine_agg

# --- ADMIN: Visualizza ordine ---
@router.get("/admin/ordini_ristorante")
def ordini_per_admin(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(403, "Utente non autenticato")

    user = db.query(models.User).get(user_id)
    if not user or not user.ristoranti:
        raise HTTPException(403, "Utente non valido o senza ristoranti")

    ristorante_ids = [r.id for r in user.ristoranti]

    ordini = (
        db.query(models.Ordine)
        .options(joinedload(models.Ordine.righe).joinedload(models.OrderItem.prodotto))
        .filter(models.Ordine.ristorante_id.in_(ristorante_ids), models.Ordine.inviato.is_(True))
        .order_by(models.Ordine.data_ordine.desc())
        .all()
    )

    # ⚠️ forza il refresh da DB, così legge l'update manuale
    for ordine in ordini:
        db.refresh(ordine)

    dati = []
    for o in ordini:
        for r in o.righe:
            dati.append({
                "ristorante": o.ristorante.nome,
                "order_manager": o.user.email,
                "data_ordine": o.data_ordine.strftime("%Y-%m-%d %H:%M"),
                "prodotto": r.prodotto.nome if r.prodotto else "—",
                "quantita": r.quantita,
                "prezzo_unitario": r.prezzo_unitario,
                "prezzo_totale": r.quantita * r.prezzo_unitario,
                "note": o.note or "",
                "inviato": o.inviato
            })
    return JSONResponse(dati)

# --- Id ristorante ---
@router.get("/ristoranti_miei")
def get_ristoranti_utente(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(403, "Utente non autenticato")

    user = db.query(models.User).get(user_id)
    if not user or not user.ristoranti:
        raise HTTPException(404, "Nessun ristorante associato")

    return [
        {"id": r.id, "nome": r.nome}
        for r in user.ristoranti
    ]
