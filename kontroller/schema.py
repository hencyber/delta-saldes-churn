"""Datakontroll som kvalitetsgrind. Kör:  python -m kontroller.schema data/kundbas.csv

Kontrollerar kolumner, datatyper och värden. Avslutas med kod 1 om datan inte
godkänns, så att pipelinen stoppas innan träningen.
"""

import sys

import pandas as pd
import pandera.pandas as pa

SCHEMA = pa.DataFrameSchema(
    {
        # unique=True fångar dubblerade kund_id
        "kund_id": pa.Column(int, unique=True),
        # coerce=True gör att saknade åldrar blir ett tydligt fel (nullable=False)
        # i stället för ett förvirrande typfel
        "alder": pa.Column(float, pa.Check.in_range(18, 110), nullable=False, coerce=True),
        "region": pa.Column(str, pa.Check.isin(["Väst", "Norr", "Stockholm", "Mitt", "Syd"])),
        "abonnemang": pa.Column(str, pa.Check.isin(["Bas", "Standard", "Premium"])),
        "manader_som_kund": pa.Column(int, pa.Check.ge(0)),
        "manadskostnad": pa.Column(float, pa.Check.ge(0)),
        # Ingen övre gräns: högre dataförbrukning är en signal, inget schemafel
        "data_gb_per_manad": pa.Column(float, pa.Check.ge(0)),
        "supportarenden_12m": pa.Column(int, pa.Check.ge(0)),
        "avslutat": pa.Column(int, pa.Check.isin([0, 1])),
    },
    # strict=True fångar både saknade och omdöpta kolumner
    strict=True,
)


def main(sokvag: str) -> int:
    df = pd.read_csv(sokvag)
    try:
        # lazy=True samlar alla fel i en rapport i stället för att stanna vid det första
        SCHEMA.validate(df, lazy=True)
    except pa.errors.SchemaErrors as fel:
        print(fel.failure_cases.to_string())
        print(f"\n{sokvag}: {len(fel.failure_cases)} fel, datan godkänns inte.")
        return 1
    print(f"{sokvag}: godkänd ({len(df)} rader).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "data/kundbas.csv"))
