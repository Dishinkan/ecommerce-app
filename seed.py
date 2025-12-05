# app/seed.py

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models
from passlib.hash import bcrypt

def run_seed():
    db: Session = SessionLocal()

    # --- Crea ristoranti se non esistono ---
    ristoranti_data = [
        "Ristorante Milano",
        "Trattoria Roma",
        "Pizzeria Napoli",
        "Osteria Firenze"
    ]

    ristoranti = []
    for nome in ristoranti_data:
        r = db.query(models.Ristorante).filter(models.Ristorante.nome == nome).first()
        if not r:
            r = models.Ristorante(nome=nome)
            db.add(r)
            db.commit()
            db.refresh(r)
        ristoranti.append(r)

    # --- Crea ruoli se non esistono ---
    ruoli_data = ["order_manager", "window_dresser", "admin", "superuser"]
    for r in ruoli_data:
        if not db.query(models.Ruolo).filter(models.Ruolo.ruolo == r).first():
            db.add(models.Ruolo(nome=r.capitalize().replace("_", " "), ruolo=r))
    db.commit()

    # Helper per prendere ruolo
    def get_ruolo(ruolo_codice):
        return db.query(models.Ruolo).filter(models.Ruolo.ruolo == ruolo_codice).first()

    # --- Crea utenti e associa ruoli e ristoranti ---
    utenti_data = [
        {"email": "alfa@email.com", "password": "password123", "ruoli": ["order_manager"], "ristoranti": [ristoranti[0]]},
        {"email": "beta@email.com", "password": "password123", "ruoli": ["window_dresser"], "ristoranti": [ristoranti[1]]},
        {"email": "gamma@email.com", "password": "password123", "ruoli": ["admin"], "ristoranti": [ristoranti[0], ristoranti[1]]},  # admin con 2 ristoranti
        {"email": "giorgio@email.com", "password": "password123", "ruoli": ["order_manager", "window_dresser"], "ristoranti": [ristoranti[2]]},
        {"email": "mattia@email.com", "password": "password123", "ruoli": ["window_dresser", "admin"], "ristoranti": [ristoranti[1]]},
        {"email": "enrico@email.com", "password": "password123", "ruoli": ["order_manager", "admin"], "ristoranti": [ristoranti[0]]},
        {"email": "pascal@email.com", "password": "password123", "ruoli": ["order_manager", "window_dresser", "admin"], "ristoranti": [ristoranti[3]]},
        {"email": "superuser@email.com", "password": "superpassword", "ruoli": ["superuser"], "ristoranti": []},
    ]

    for udata in utenti_data:
        user = db.query(models.User).filter(models.User.email == udata["email"]).first()
        if not user:
            user = models.User(
                email=udata["email"],
                hashed_password=bcrypt.hash(udata["password"]),
                is_active=True
            )
            # associa ruoli
            user.ruoli = [get_ruolo(r) for r in udata["ruoli"]]
            # associa ristoranti (many-to-many)
            user.ristoranti = udata["ristoranti"]
            db.add(user)

    db.commit()
    db.close()

if __name__ == "__main__":
    run_seed()
    print("✅ Seed completato con ristoranti, utenti e associazioni corrette.")
