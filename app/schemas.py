# app/schemas.py

from pydantic import BaseModel, field_serializer
from typing import Optional, List
from datetime import datetime

# --------------------
# RISTORANTI
# --------------------

class RistoranteBase(BaseModel):
    nome: str
    abbonamento_attivo: Optional[bool] = True

class RistoranteCreate(RistoranteBase):
    pass

class Ristorante(RistoranteBase):
    id: int

    class Config:
        from_attributes = True

# --------------------
# RUOLI
# --------------------

class RuoloOut(BaseModel):
    ruolo: str

    class Config:
        from_attributes = True

# --------------------
# UTENTI
# --------------------

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str
    ristorante_id: Optional[int] = None
    ruoli: Optional[List[str]] = []

class User(UserBase):
    id: int
    ristorante_id: Optional[int]
    ruoli: List[RuoloOut] = []
    ristoranti: List[Ristorante] = []

    class Config:
        from_attributes = True

    @field_serializer("ruoli", when_used="always")
    def serialize_roles(self, value):
        return [r.ruolo for r in value]

    @field_serializer("ristoranti", when_used="always")
    def serialize_ristoranti(self, value):
        return [{"id": r.id, "nome": r.nome} for r in value]

# --------------------
# PAYLOAD APPROVAZIONE SUPERUSER
# --------------------

class ApprovePayload(BaseModel):
    ristorante_id: Optional[int] = None
    nome_ristorante: Optional[str] = None
    ruoli: Optional[List[str]] = None

# --------------------
# FORNITORI
# --------------------

class FornitoreBase(BaseModel):
    nome: str
    email: Optional[str] = None

class FornitoreCreate(FornitoreBase):
    pass

class Fornitore(FornitoreBase):
    id: int

    class Config:
        from_attributes = True

# --------------------
# PRODOTTI
# --------------------

class ProdottoBase(BaseModel):
    nome: str
    descrizione: Optional[str] = None
    prezzo: float
    immagine_url: Optional[str] = None
    fornitore_id: int

class ProdottoCreate(ProdottoBase):
    pass

class Prodotto(ProdottoBase):
    id: int
    fornitore: Optional[Fornitore] = None

    class Config:
        from_attributes = True

# --------------------
# ORDER ITEM
# --------------------

class OrderItemBase(BaseModel):
    prodotto_id: int
    quantita: int

class OrderItemCreate(OrderItemBase):
    pass

class OrderItem(OrderItemBase):
    id: int
    prezzo_unitario: float
    prodotto: Optional[Prodotto] = None

    class Config:
        from_attributes = True

# --------------------
# ORDINI
# --------------------

class OrdineBase(BaseModel):
    note: Optional[str] = None

class OrdineCreate(OrdineBase):
    ristorante_id: int
    righe: List[OrderItemCreate]

class Ordine(OrdineBase):
    id: int
    user_id: int
    ristorante_id: int
    data_ordine: datetime
    totale: float
    righe: Optional[List[OrderItem]] = []

    class Config:
        from_attributes = True
