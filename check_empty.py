from app.database import SessionLocal
from app import models

db = SessionLocal()

users_count = db.query(models.User).count()
ristoranti_count = db.query(models.Ristorante).count()
prodotti_count = db.query(models.Prodotto).count()
ordini_count = db.query(models.Ordine).count()

print(f"Users: {users_count}")
print(f"Ristoranti: {ristoranti_count}")
print(f"Prodotti: {prodotti_count}")
print(f"Ordini: {ordini_count}")

db.close()
