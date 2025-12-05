# app/jobs.py

import asyncio
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models
from app.email_utils import invia_mail
import logging


async def invia_ordini():
    db: Session = SessionLocal()
    print(f"[{datetime.now()}] Esecuzione job invio ordini aggregati...")

    try:
        # Prendo SOLO gli ordini aggregati non inviati
        ordini = db.query(models.Ordine)\
                   .filter(models.Ordine.inviato == False)\
                   .all()

        for ordine in ordini:
            order_manager_email = ordine.user.email
            righe = ordine.righe

            # Preparo testo mail per order manager
            testo_mail_om = f"Riepilogo ordine #{ordine.id} — Ristorante {ordine.ristorante.nome}\n\n"

            # Raggruppo righe per fornitore
            fornitori = {}  # {email_fornitore: [linee]}
            for r in righe:
                prodotto = r.prodotto
                subtot = r.quantita * r.prezzo_unitario
                linea = f"- {prodotto.nome} x {r.quantita} = {subtot:.2f}€\n"
                testo_mail_om += linea

                # Raggruppo per fornitore
                email_forn = prodotto.fornitore.email
                if email_forn not in fornitori:
                    fornitori[email_forn] = []
                fornitori[email_forn].append(linea)

            testo_mail_om += f"\nTotale ordine aggregato: {ordine.totale:.2f}€"

            # 1️⃣ Invio mail all’order manager (mittente = stesso order manager)
            await invia_mail(
                destinatario=order_manager_email,
                oggetto=f"Conferma ordine aggregato #{ordine.id}",
                corpo=testo_mail_om,
                mittente=order_manager_email
            )

            # 2️⃣ Invio mail a ciascun fornitore
            for email_forn, righe_txt in fornitori.items():
                corpo = f"Ordine dal ristorante {ordine.ristorante.nome} (#{ordine.id}):\n" + "".join(righe_txt)
                await invia_mail(
                    destinatario=email_forn,
                    oggetto=f"Nuovo ordine #{ordine.id}",
                    corpo=corpo,
                    mittente=order_manager_email
                )

            # Segno ordine come inviato
            ordine.inviato = True

        db.commit()
        print(f"{len(ordini)} ordine/i aggregato/i processato/i e inviato/i.\n")

    except Exception as e:
        db.rollback()
        logging.exception("Job invio ordini fallito")
    finally:
        db.close()


def run_job_sync():
    asyncio.run(invia_ordini())


# Scheduler che invia tutti gli ordini aggregati ogni giorno alle 16:00
scheduler = BackgroundScheduler()
scheduler.add_job(run_job_sync, 'cron', hour=16, minute=0)
scheduler.start()
