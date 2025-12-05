# app/main.py

import os
from fastapi import FastAPI, Request, Form, HTTPException, Body, Depends
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles
from passlib.hash import bcrypt
from sqlalchemy.orm import joinedload, Session
from sqlalchemy.exc import IntegrityError
from typing import List

from app import models
from app.database import SessionLocal
from app.routers import prodotti as prodotti_router
from app.routers import ordini as ordini_router
from app.routers import ristoranti as ristoranti_router
from app.config import BASE_DIR, STATIC_DIR, UPLOADS_DIR

app = FastAPI()

# --- Sessioni ---
app.add_middleware(SessionMiddleware, secret_key="supersecretkey")

# --- Templates ---
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# --- Static / Uploads ---
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- Helpers ---
def get_user_by_email(email: str):
    db = SessionLocal()
    user = (
        db.query(models.User)
        .options(joinedload(models.User.ruoli))
        .filter(models.User.email == email)
        .first()
    )
    db.close()
    return user

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Homepage ---
@app.get("/", response_class=HTMLResponse)
def welcome(request: Request):
    return templates.TemplateResponse("welcome.html", {"request": request})

# --- Auth (login) ---
@app.get("/auth", response_class=HTMLResponse)
def auth_form(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request})

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    user = get_user_by_email(email)
    if not user or not bcrypt.verify(password, user.hashed_password):
        return templates.TemplateResponse(
            "auth.html",
            {"request": request, "error": "Email o password non validi"},
        )
    if not user.is_active:
        return templates.TemplateResponse(
            "auth.html",
            {"request": request, "error": "Account in attesa di approvazione"},
        )

    request.session["user_id"] = user.id
    request.session["user_email"] = user.email
    request.session["ruoli"] = [ruolo.ruolo for ruolo in user.ruoli]
    return RedirectResponse("/dashboard", status_code=302)

# --- Auth (registrazione) ---
@app.post("/register", response_class=HTMLResponse)
def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
    nome_ristorante: str = Form(...),
    ruoli: List[str] = Form([]),
):
    if password != password2:
        return templates.TemplateResponse(
            "auth.html",
            {"request": request, "error": "Le password non coincidono"},
        )

    db = SessionLocal()
    try:
        hashed = bcrypt.hash(password)

        # --- Creiamo direttamente l'utente (is_active=False) ---
        user = models.User(
            email=email,
            hashed_password=hashed,
            is_active=False,  # utente in attesa
            ristorante_richiesto=nome_ristorante
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Associa ruoli richiesti se presenti
        if ruoli:
            ruoli_obj = db.query(models.Ruolo).filter(models.Ruolo.ruolo.in_(ruoli)).all()
            user.ruoli_richiesti = ruoli_obj
            db.commit()

        # Eventuale associazione ruoli richiesta
        if ruoli:
            ruoli_obj = db.query(models.Ruolo).filter(models.Ruolo.ruolo.in_(ruoli)).all()
            user.ruoli_richiesti = ruoli_obj  # se vuoi memorizzare richieste
            db.commit()

    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            "auth.html",
            {"request": request, "error": "Email già registrata"},
        )
    finally:
        db.close()

    return templates.TemplateResponse(
        "auth.html",
        {"request": request, "error": "Registrazione completata! Attendi approvazione."},
    )

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse("/", status_code=302)

    ruoli = request.session.get("ruoli", [])
    if not ruoli:  # nessun ruolo assegnato
        return templates.TemplateResponse(
            "pending.html",  # nuovo template
            {
                "request": request,
                "user": {
                    "email": request.session.get("user_email"),
                    "ruoli": [],
                },
            },
        )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": {
                "email": request.session.get("user_email"),
                "ruoli": ruoli,
            },
        },
    )
@app.get("/dashboard/order_manager/order_aggregato", response_class=HTMLResponse)
def dashboard_aggregato(request: Request, ristorante_id: int = None, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse("/", status_code=302)

    user_id = request.session.get("user_id")
    user = db.query(models.User).get(user_id)
    if not user or not user.ristoranti:
        return HTMLResponse("<h2>Nessun ristorante associato</h2>")

    if ristorante_id is None:
        ristorante_id = user.ristoranti[0].id

    ristorante = db.query(models.Ristorante).filter(models.Ristorante.id == ristorante_id).first()
    if not ristorante:
        return HTMLResponse("<h2>Ristorante non trovato</h2>")

    return templates.TemplateResponse(
        "dashboards/order_aggregato.html",
        {
            "request": request,
            "ristorante": ristorante
        }
    )
    
@app.get("/dashboard/{ruolo}", response_class=HTMLResponse)
@app.get("/dashboard/{ruolo}/{ristorante_id}", response_class=HTMLResponse)
def dashboard_ruolo(request: Request, ruolo: str, ristorante_id: int | None = None):
    if not request.session.get("user_id"):
        return RedirectResponse("/", status_code=302)

    ruoli_utente = request.session.get("ruoli", [])
    email_utente = request.session.get("user_email")

    # Superuser vede tutto, altrimenti solo i ruoli assegnati
    if "superuser" in ruoli_utente or ruolo in ruoli_utente:
        db = SessionLocal()
        try:
            user_obj = db.query(models.User).options(
                joinedload(models.User.ristoranti)
                .joinedload(models.Ristorante.prodotti_visibili)
            ).filter(models.User.email == email_utente).first()

            if ruolo == "order_manager":
                ristoranti = user_obj.ristoranti

                if not ristoranti:
                    return HTMLResponse("<h2>Nessun ristorante associato</h2>")

                # Se l'utente non ha scelto un ristorante e ne ha più di uno → pagina di selezione
                if ristorante_id is None:
                    if len(ristoranti) == 1:
                        ristorante_id = ristoranti[0].id
                    else:
                        return templates.TemplateResponse(
                            "dashboards/order_manager_select.html",
                            {"request": request, "ristoranti": ristoranti},
                        )

                # Recupero il ristorante selezionato
                ristorante = db.query(models.Ristorante).filter(
                    models.Ristorante.id == ristorante_id
                ).first()
                if not ristorante:
                    return HTMLResponse("<h2>Ristorante non trovato</h2>")

                prodotti = ristorante.prodotti_visibili

                return templates.TemplateResponse(
                    "dashboards/order_manager.html",
                    {
                        "request": request,
                        "user": user_obj,
                        "prodotti": prodotti,
                        "ristorante": ristorante,
                    },
                )

            # altri ruoli → come prima
            return templates.TemplateResponse(
                f"dashboards/{ruolo}.html",
                {"request": request, "user": user_obj},
            )
        finally:
            db.close()

    # se il ruolo non è autorizzato
    return HTMLResponse("<h2>Accesso negato</h2>", status_code=403)

# --- Superuser: utenti in attesa ---
@app.get("/users/pending")
def users_pending(request: Request):
    user_id = request.session.get("user_id")
    ruoli = request.session.get("ruoli", [])
    if not user_id or "superuser" not in ruoli:
        return JSONResponse({"error": "Accesso negato"}, status_code=403)

    db = SessionLocal()
    try:
        pending_users = db.query(models.User) \
                          .options(joinedload(models.User.ruoli_richiesti)) \
                          .filter(models.User.is_active == False) \
                          .all()

        users_list = []
        for u in pending_users:
            users_list.append({
                "id": u.id,
                "email": u.email,
                "ruoli_richiesti": [r.ruolo for r in u.ruoli_richiesti],
                "ristorante_richiesto": getattr(u, "ristorante_richiesto", None)
            })
        return JSONResponse(users_list)
    finally:
        db.close()

@app.put("/users/pending/approve/{user_id}")
def approve_user(user_id: int, payload: dict = Body({}), request: Request = None):
    user_id_session = request.session.get("user_id") if request else None
    ruoli_session = request.session.get("ruoli") if request else []

    if not user_id_session or "superuser" not in ruoli_session:
        raise HTTPException(status_code=403, detail="Accesso negato")

    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Utente non trovato")

        # Gestione ristorante
        ristorante_id = payload.get("ristorante_id")
        nome_ristorante = payload.get("nome_ristorante")

        if ristorante_id:
            ristorante = db.query(models.Ristorante).filter(models.Ristorante.id == ristorante_id).first()
            if not ristorante:
                raise HTTPException(status_code=404, detail="Ristorante non trovato")
        elif nome_ristorante:
            ristorante = models.Ristorante(nome=nome_ristorante)
            db.add(ristorante)
            db.commit()
            db.refresh(ristorante)
        else:
            raise HTTPException(status_code=400, detail="Serve un ristorante da associare")

        user.ristorante_id = ristorante.id
        user.is_active = True

        # Associa ruoli
        ruoli = payload.get("ruoli", [])
        if ruoli:
            ruoli_obj = db.query(models.Ruolo).filter(models.Ruolo.ruolo.in_(ruoli)).all()
            user.ruoli = ruoli_obj

        db.commit()
        return {"ok": True, "msg": "Utente approvato"}

    finally:
        db.close()

# --- Superuser: modifica associazione ristoranti ---
@app.put("/users/{user_id}/ristoranti")
def modify_user_ristorante(user_id: int, payload: dict = Body(...), db: Session = Depends(get_db), request: Request = None):
    user_id_session = request.session.get("user_id") if request else None
    ruoli_session = request.session.get("ruoli") if request else []
    if not user_id_session or "superuser" not in ruoli_session:
        raise HTTPException(status_code=403, detail="Accesso negato")

    user = db.query(models.User).options(joinedload(models.User.ristoranti)).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    ristorante_id = payload.get("ristorante_id")
    action = payload.get("action")

    ristorante = db.query(models.Ristorante).filter(models.Ristorante.id == ristorante_id).first()
    if not ristorante:
        raise HTTPException(status_code=404, detail="Ristorante non trovato")

    if action == "add" and ristorante not in user.ristoranti:
        user.ristoranti.append(ristorante)
    elif action == "remove" and ristorante in user.ristoranti:
        user.ristoranti.remove(ristorante)

    db.commit()
    return {"ok": True}

@app.get("/users/active")
def users_active(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    ruoli = request.session.get("ruoli", [])
    if not user_id or "superuser" not in ruoli:
        raise HTTPException(status_code=403, detail="Accesso negato")
    
    users = db.query(models.User).options(joinedload(models.User.ristoranti)) \
        .filter(models.User.is_active == True).all()

    return JSONResponse([
        {
            "id": u.id,
            "email": u.email,
            "ristoranti_ids": [r.id for r in u.ristoranti]
        }
        for u in users
    ])

# --- Order manager: ordince completo del giorno ---
@app.get("/dashboard/order_manager/order_aggregato", response_class=HTMLResponse)
def dashboard_aggregato(request: Request):
    print("⚡ DEBUG: entrato in /dashboard/order_manager/order_aggregato")  # DEBUG
    if not request.session.get("user_id"):
        print("⚡ DEBUG: utente non autenticato, redirect /")  # DEBUG
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("dashboards/order_aggregato.html", {"request": request})

# --- Logout ---
@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)

# --- Routers API ---
app.include_router(prodotti_router.router)
app.include_router(ristoranti_router.router)
app.include_router(ordini_router.router)
