from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import models  # Assicurati che models.py abbia le classi Fornitore e Prodotto
import os

# --- Configurazione DB ---
DB_URL = "sqlite:///C:/Users/Gatti/Desktop/Lavoro Aziende/ecommerce-app/sql_app.db"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
models.Base.metadata.create_all(bind=engine)  # crea le tabelle mancanti
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# --- Dati fornitori e prodotti con email ---
fornitori_info = {
    "Ortofrutta": {
        "email": "ortofrutta@example.com",
        "prodotti": [f"FruttaVerdura_{i}" for i in range(1, 11)]
    },
    "Carne": {
        "email": "carne@example.com",
        "prodotti": [f"Carne_{i}" for i in range(1, 11)]
    },
    "Pesce": {
        "email": "pesce@example.com",
        "prodotti": [f"Pesce_{i}" for i in range(1, 11)]
    },
    "Attrezzatura": {
        "email": "attrezzatura@example.com",
        "prodotti": [f"Attrezzatura_{i}" for i in range(1, 11)]
    },
}

# --- Creazione fornitori e prodotti ---
for nome_fornitore, info in fornitori_info.items():
    email_fornitore = info["email"]
    prodotti_list = info["prodotti"]

    # Controlla se il fornitore esiste
    fornitore = db.query(models.Fornitore).filter(models.Fornitore.nome == nome_fornitore).first()
    if not fornitore:
        fornitore = models.Fornitore(nome=nome_fornitore, email=email_fornitore)
        db.add(fornitore)
        db.commit()
        db.refresh(fornitore)

    # Creazione prodotti
    for prodotto_nome in prodotti_list:
        prodotto = models.Prodotto(
            nome=prodotto_nome,
            prezzo=round(1 + 99 * os.urandom(1)[0]/255, 2),  # prezzo casuale tra 1 e 100
            fornitore_id=fornitore.id
        )
        db.add(prodotto)

db.commit()
db.close()
print("Fornitori e prodotti creati con successo!")
