# app/dependencies.py

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import joinedload
from app.database import SessionLocal
from app import models

def get_current_user(request: Request) -> models.User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Non autenticato")
    db = SessionLocal()
    try:
        user = (
            db.query(models.User)
            .options(joinedload(models.User.ruoli))
            .get(user_id)
        )
        if not user:
            raise HTTPException(status_code=401, detail="Utente non trovato")
        return user
    finally:
        db.close()

def require_role(*accepted_roles: str):
    def _dep(user: models.User = Depends(get_current_user)) -> models.User:
        user_roles = {r.ruolo for r in user.ruoli}
        if "superuser" in user_roles:
            return user
        if not user_roles.intersection(set(accepted_roles)):
            raise HTTPException(status_code=403, detail="Non autorizzato")
        return user
    return _dep
