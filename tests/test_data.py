"""Testnivå 2: data. Ser datan ut som vi tror?"""

from churn.data import FEATURES, MAL, las_data, skapa_features


def test_forvantade_kolumner_finns():
    df = skapa_features(las_data())
    assert set(FEATURES + [MAL]) <= set(df.columns)


def test_malvariabeln_ar_binar():
    assert set(las_data()[MAL].unique()) <= {0, 1}


def test_kund_id_ar_unikt():
    # Dubbletter ger samma kund två gånger i ringlistan och väger tyngre i träningen.
    assert las_data()["kund_id"].is_unique


def test_alder_ar_rimlig():
    # Brett intervall så att giltiga kunder inte fäller testet, men fel som -81 fångas.
    alder = las_data()["alder"]
    assert alder.notna().all()
    assert alder.between(18, 100).all()
