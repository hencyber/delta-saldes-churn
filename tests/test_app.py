"""API:t i src/churn/app.py. Tränar en modell till en tillfällig mapp, så att testet
inte är beroende av att outputs/ finns på datorn (samma fälla som i ärende F2)."""

import importlib
import json

import joblib
import pytest
from fastapi.testclient import TestClient

from churn.model import trana_och_utvardera

KUND = {
    "alder": 34,
    "region": " stockholm",
    "abonnemang": "Standard",
    "manader_som_kund": 12,
    "manadskostnad": 299.0,
    "data_gb_per_manad": 9.0,
    "supportarenden_12m": 2,
}


@pytest.fixture(scope="module")
def klient(tmp_path_factory, monkeypatch_module):
    katalog = tmp_path_factory.mktemp("outputs")
    modell, matvarden = trana_och_utvardera()
    matvarden["commit"] = "test"
    joblib.dump(modell, katalog / "modell.joblib")
    (katalog / "matvarden.json").write_text(json.dumps(matvarden))

    monkeypatch_module.setenv("MODELLFIL", str(katalog / "modell.joblib"))
    import churn.app

    app_modul = importlib.reload(churn.app)
    with TestClient(app_modul.app) as klient:
        yield klient


@pytest.fixture(scope="module")
def monkeypatch_module():
    with pytest.MonkeyPatch.context() as mp:
        yield mp


def test_health(klient):
    svar = klient.get("/health")
    assert svar.status_code == 200
    assert svar.json()["status"] == "ok"
    assert svar.json()["commit"] == "test"


def test_predict_ger_en_sannolikhet(klient):
    svar = klient.post("/predict", json=KUND)
    assert svar.status_code == 200
    assert 0 <= svar.json()["risk"] <= 1


def test_predict_avvisar_orimlig_alder(klient):
    svar = klient.post("/predict", json={**KUND, "alder": -5})
    assert svar.status_code == 422


def test_health_utan_modell(tmp_path, monkeypatch):
    monkeypatch.setenv("MODELLFIL", str(tmp_path / "finns_inte.joblib"))
    import churn.app

    app_modul = importlib.reload(churn.app)
    with TestClient(app_modul.app) as klient:
        assert klient.get("/health").status_code == 503
