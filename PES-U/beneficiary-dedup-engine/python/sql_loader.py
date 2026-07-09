"""
sql_loader.py  —  Phase 1: fetch records from the PostgreSQL HCM schema and
produce the same Beneficiary objects the engine already scores.

The five source tables are joined back into the flat record shape the CSV
loader produced, so NOTHING in the dedup engine changes — only the data source
does. This is the whole point of Phase 1: prove the engine gives the same
precision/recall on relational data as it did on the CSV.

Requires:  pip install psycopg2-binary
Usage:
    from sql_loader import load_records_from_sql
    records = load_records_from_sql(dbname="hcm", user="postgres", password="...")

Connection settings can also come from environment variables so the password
is not hardcoded:
    PGHOST, PGDATABASE, PGUSER, PGPASSWORD, PGPORT
"""

import os
from datetime import datetime
from typing import List, Optional

import psycopg2

from models.candidate_pair import Beneficiary


# ── The fetch query ────────────────────────────────────────────────────────
# One row per individual, reconstructing the flat record from 5 tables.
# LEFT JOIN on address/beneficiary so a missing row never drops a person.
FETCH_SQL = """
SELECT
    i.client_reference_id            AS individual_client_ref,
    n.given_name                     AS given_name,
    n.family_name                    AS family_name,
    i.gender                         AS gender,
    i.date_of_birth                  AS date_of_birth,
    i.father_name                    AS father_name,
    i.husband_name                   AS husband_name,
    i.mobile_number                  AS mobile_number,
    i.boundary_code                  AS boundary_code,
    a.latitude                       AS latitude,
    a.longitude                      AS longitude,
    a.location_accuracy              AS location_accuracy,
    a.locality_name                  AS locality_name,
    i.tenant_id                      AS tenant_id,
    pb.additional_fields->>'cycle'   AS cycle
FROM individual i
JOIN individual_name n
    ON n.individual_client_reference_id = i.client_reference_id
LEFT JOIN individual_address a
    ON a.related_client_reference_id = i.client_reference_id
LEFT JOIN project_beneficiary pb
    ON pb.beneficiary_client_reference_id = i.client_reference_id
"""


def _to_str(v) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _to_float(v) -> Optional[float]:
    try:
        return float(v) if v is not None and str(v).strip() != "" else None
    except (ValueError, TypeError):
        return None


def _to_date(v):
    """psycopg2 returns DATE columns as datetime.date already; handle str too."""
    if v is None:
        return None
    if hasattr(v, "year") and hasattr(v, "month"):  # a date/datetime
        return v if not hasattr(v, "date") else v.date() if isinstance(v, datetime) else v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _connect(dbname, user, password, host, port):
    return psycopg2.connect(
        dbname=dbname or os.environ.get("PGDATABASE", "hcm"),
        user=user or os.environ.get("PGUSER", "postgres"),
        password=password or os.environ.get("PGPASSWORD", ""),
        host=host or os.environ.get("PGHOST", "localhost"),
        port=port or os.environ.get("PGPORT", "5432"),
    )


def load_records_from_sql(dbname="hcm", user="postgres", password=None,
                          host="localhost", port="5432",
                          where_cycle=None) -> List[Beneficiary]:
    """
    Fetch all individuals as normalized Beneficiary objects.

    where_cycle: optional cycle filter (e.g. "3") to fetch only one cycle,
                 matching how the on-device app would query a single drive.
    """
    sql = FETCH_SQL
    params = None
    if where_cycle is not None:
        sql = sql + " WHERE pb.additional_fields->>'cycle' = %s"
        params = (str(where_cycle),)

    conn = _connect(dbname, user, password, host, port)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        records: List[Beneficiary] = []
        for row in cur.fetchall():
            r = dict(zip(cols, row))
            rec = Beneficiary(
                individual_id     = str(r["individual_client_ref"]),
                given_name        = _to_str(r["given_name"]),
                family_name       = _to_str(r["family_name"]),
                father_name       = _to_str(r["father_name"]),
                husband_name      = _to_str(r["husband_name"]),
                gender            = _to_str(r["gender"]),
                date_of_birth     = _to_date(r["date_of_birth"]),
                boundary_code     = _to_str(r["boundary_code"]),
                locality_name     = _to_str(r["locality_name"]),
                latitude          = _to_float(r["latitude"]),
                longitude         = _to_float(r["longitude"]),
                location_accuracy = _to_float(r["location_accuracy"]),
                mobile_number     = _to_str(r["mobile_number"]),
                cycle             = _to_str(r["cycle"]),
            )
            rec.normalize()
            records.append(rec)
        return records
    finally:
        conn.close()


if __name__ == "__main__":
    # Quick smoke test
    import sys
    pw = os.environ.get("PGPASSWORD") or (sys.argv[1] if len(sys.argv) > 1 else "")
    recs = load_records_from_sql(password=pw)
    print(f"Loaded {len(recs):,} records from SQL")
    for r in recs[:3]:
        print(f"  {r.given_name} {r.family_name} | father {r.father_name} | "
              f"dob {r.date_of_birth} | cycle {r.cycle} | "
              f"gps ({r.latitude},{r.longitude})")
    cyc = {}
    for r in recs:
        cyc[r.cycle] = cyc.get(r.cycle, 0) + 1
    print("Cycle distribution:", dict(sorted(cyc.items(), key=lambda x: str(x[0]))))
