# app/models.py

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, Float, DateTime
from sqlalchemy.orm import relationship, backref
from .database import Base
from datetime import datetime

# -------------------------
# Tabelle di associazione
# -------------------------

# Associazione utenti <-> ruoli (many-to-many)
user_ruoli = Table(
    "user_ruoli",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("ruolo_id", Integer, ForeignKey("ruoli.id"), primary_key=True),
)

# Associazione ristoranti <-> prodotti visibili (many-to-many)
product_visibility = Table(
    "product_visibility",
    Base.metadata,
    Column("ristorante_id", Integer, ForeignKey("ristoranti.id"), primary_key=True),
    Column("prodotto_id", Integer, ForeignKey("prodotti.id"), primary_key=True),
)

# Associazione Registrazione <-> Ruoli richiesti
registrazione_ruoli = Table(
    "registrazione_ruoli",
    Base.metadata,
    Column("registrazione_id", Integer, ForeignKey("registrazioni_pending.id"), primary_key=True),
    Column("ruolo_id", Integer, ForeignKey("ruoli.id"), primary_key=True),
)

user_ruoli_richiesti = Table(
    "user_ruoli_richiesti",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("ruolo_id", Integer, ForeignKey("ruoli.id"), primary_key=True),
)

# Associazione utenti <-> ristoranti (many-to-many)
user_ristoranti = Table(
    "user_ristoranti",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("ristorante_id", Integer, ForeignKey("ristoranti.id"), primary_key=True),
)

# -------------------------
# MODELS
# -------------------------

class RegistrazionePending(Base):
    __tablename__ = "registrazioni_pending"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Nome ristorante richiesto (se non esiste lo crea il superuser)
    ristorante_richiesto = Column(String, nullable=False)

    data_creazione = Column(DateTime, default=datetime.utcnow)
    approvata = Column(Boolean, default=False)

    # relazioni
    ruoli_richiesti = relationship("Ruolo", secondary=registrazione_ruoli)

class Ristorante(Base):
    __tablename__ = "ristoranti"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True, nullable=False)
    abbonamento_attivo = Column(Boolean, default=True)

    # relazioni
    utenti = relationship(
        "User",
        secondary=user_ristoranti,
        back_populates="ristoranti"
    )
    prodotti_visibili = relationship(
        "Prodotto",
        secondary=product_visibility,
        back_populates="visibile_in"
    )

class Ruolo(Base):
    __tablename__ = "ruoli"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True)
    ruolo = Column(String, unique=True)

    users = relationship("User", secondary=user_ruoli, back_populates="ruoli")
    users_pending = relationship(
        "User",
        secondary=user_ruoli_richiesti,
        back_populates="ruoli_richiesti"
    )

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    # relazione many-to-many ristoranti
    ristoranti = relationship(
        "Ristorante",
        secondary=user_ristoranti,
        back_populates="utenti"
    )

    # ruoli
    ruoli = relationship("Ruolo", secondary=user_ruoli, back_populates="users")
    
    # Nuova relazione per ruoli richiesti (solo utenti pending)
    ristorante_richiesto = Column(String, nullable=True)
    ruoli_richiesti = relationship(
        "Ruolo",
        secondary=user_ruoli_richiesti,
        back_populates="users_pending"
    )

class Fornitore(Base):
    __tablename__ = "fornitori"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, nullable=True)

    prodotti = relationship("Prodotto", back_populates="fornitore")

class Prodotto(Base):
    __tablename__ = "prodotti"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True, nullable=False)
    descrizione = Column(String, nullable=True)
    prezzo = Column(Float, nullable=False)
    immagine_url = Column(String, nullable=True)

    fornitore_id = Column(Integer, ForeignKey("fornitori.id"))

    # relazioni
    fornitore = relationship("Fornitore", back_populates="prodotti")
    visibile_in = relationship(
        "Ristorante",
        secondary=product_visibility,
        back_populates="prodotti_visibili"
    )
    ordini = relationship("OrderItem", back_populates="prodotto")

class Ordine(Base):
    __tablename__ = "ordini"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    ristorante_id = Column(Integer, ForeignKey("ristoranti.id"))
    data_ordine = Column(DateTime, default=datetime.utcnow)
    totale = Column(Float, nullable=False, default=0.0)
    note = Column(String, nullable=True)
    inviato = Column(Boolean, default=False)

    # relazioni
    user = relationship("User")
    ristorante = relationship("Ristorante")
    righe = relationship("OrderItem", back_populates="ordine")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    ordine_id = Column(Integer, ForeignKey("ordini.id"))
    prodotto_id = Column(Integer, ForeignKey("prodotti.id"))
    quantita = Column(Integer, nullable=False)
    prezzo_unitario = Column(Float, nullable=False)

    # relazioni
    ordine = relationship("Ordine", back_populates="righe")
    prodotto = relationship("Prodotto", back_populates="ordini")
