# app/email_utils.py

import os
from email.message import EmailMessage
import aiosmtplib
import logging
from app.database import SessionLocal
from app import models

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.ethereal.email")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "your_ethereal_user")
SMTP_PASS = os.getenv("SMTP_PASS", "your_ethereal_pass")
FROM = os.getenv("EMAIL_FROM", SMTP_USER)

async def invia_mail(destinatario: str, oggetto: str, corpo: str, mittente: str = None):
    mittente = mittente or FROM  # se mittente non passato, usa default
    msg = EmailMessage()
    msg["From"] = mittente
    msg["To"] = destinatario
    msg["Subject"] = oggetto
    msg.set_content(corpo)
    
    try:
        resp = await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            start_tls=True,
            username=SMTP_USER,
            password=SMTP_PASS,
        )
        logging.info("Mail inviata a %s — risposta: %s", destinatario, resp)
    except Exception as e:
        logging.exception("Errore invio mail a %s: %s", destinatario, e)
        raise
        
async def invia_ordine(ordine: models.Ordine):
    db = SessionLocal()
    try:
        ordine = db.query(models.Ordine).get(ordine.id)
        user = ordine.user
        righe = ordine.righe
        testo_mail_user = f"Riepilogo ordine #{ordine.id} — Ristorante {ordine.ristorante.nome}\n\n"

        fornitori = {}
        for r in righe:
            prodotto = r.prodotto
            linea = f"- {prodotto.nome} x {r.quantita} = {r.quantita * r.prezzo_unitario:.2f}€\n"
            testo_mail_user += linea
            fornitori.setdefault(prodotto.fornitore.email, []).append(linea)

        testo_mail_user += f"\nTotale ordine: {ordine.totale:.2f}€"

        # invia mail utente
        await invia_mail(user.email, f"Conferma ordine #{ordine.id}", testo_mail_user)

        # invia mail fornitori
        for email_forn, righe_txt in fornitori.items():
            corpo = f"Ordine dal ristorante {ordine.ristorante.nome} (#{ordine.id}):\n" + "".join(righe_txt)
            await invia_mail(email_forn, f"Nuovo ordine #{ordine.id}", corpo)

        ordine.inviato = True
        db.commit()
    finally:
        db.close()
