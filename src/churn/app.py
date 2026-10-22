"""API som serverar den godkända modellen. Kör:  uvicorn churn.app:app

Modellen tränas inte här. Den läses från MODELLFIL (standard outputs/modell.joblib),
som i Docker-imagen är modellen från train-jobbets artefakt. Mätvärdena i
matvarden.json bredvid modellen visas i /health, så man kan se vilken commit och
vilken data modellen i containern kom från.

Endpoints:
  GET  /health   200 om modellen är laddad, annars 503. Används av smoke-testet.
  POST /predict  risken att en kund avslutar sitt abonnemang.
"""

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from churn.data import FEATURES, skapa_features

MODELLFIL = Path(os.environ.get("MODELLFIL", "outputs/modell.joblib"))

# Fylls i vid start. En tom dict betyder att modellen inte gick att ladda.
tillstand: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Laddas en gång när servern startar, inte vid varje anrop.
    if MODELLFIL.exists():
        tillstand["modell"] = joblib.load(MODELLFIL)
        matvardesfil = MODELLFIL.with_name("matvarden.json")
        if matvardesfil.exists():
            tillstand["matvarden"] = json.loads(matvardesfil.read_text())
    yield
    tillstand.clear()


app = FastAPI(title="Saldes churnmodell", lifespan=lifespan)


class Kund(BaseModel):
    """En kund, med samma kolumner som i data/kundbas.csv (utom kund_id och avslutat)."""

    alder: float = Field(ge=18, le=110)
    region: str
    abonnemang: str
    manader_som_kund: int = Field(ge=0)
    manadskostnad: float = Field(ge=0)
    data_gb_per_manad: float = Field(ge=0)
    supportarenden_12m: int = Field(ge=0)


@app.get("/health")
def health() -> dict:
    if "modell" not in tillstand:
        raise HTTPException(status_code=503, detail=f"Ingen modell laddad från {MODELLFIL}")
    matvarden = tillstand.get("matvarden", {})
    return {
        "status": "ok",
        "commit": matvarden.get("commit"),
        "roc_auc": matvarden.get("roc_auc"),
        "data_sha256": matvarden.get("data_sha256"),
    }


@app.post("/predict")
def predict(kund: Kund) -> dict:
    if "modell" not in tillstand:
        raise HTTPException(status_code=503, detail="Ingen modell laddad")
    # Samma feature-kod som vid träningen, så att indata behandlas likadant.
    X = skapa_features(pd.DataFrame([kund.model_dump()]))[FEATURES]
    risk = float(tillstand["modell"].predict_proba(X)[0, 1])
    return {"risk": round(risk, 3)}
