"""
digit_dedup_engine.py   <->   lib/digit_dedup_engine.dart   (library barrel)

Public API surface. In Dart this is the file consumers import:

    import 'package:digit_dedup_engine/digit_dedup_engine.dart';

It re-exports the public symbols and provides a CSV loader for the reference /
benchmark workflow. (The Dart barrel exports classes; CSV loading is Python-only
since on-device data comes from SQLite, not CSV.)
"""

import csv
from datetime import datetime
from typing import List, Optional

# Re-exports (the public surface)
from models.candidate_pair import Beneficiary, CandidatePair          # noqa: F401
from models.dedup_result import DedupResult, DUPLICATE, REVIEW, CLEAR # noqa: F401
from dedup_engine import check_for_duplicates, run_batch              # noqa: F401
from matching_service import score_pair, DEFAULT_WEIGHTS, THRESHOLDS  # noqa: F401
from blocking_strategy import build_candidate_pairs                   # noqa: F401


_DATE_FORMATS = ["%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]


def _parse_date(raw):
    if not raw:
        return None
    s = str(raw).strip()
    if s == "" or s.lower() in ("nan", "none"):
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _to_float(raw) -> Optional[float]:
    try:
        if raw is None:
            return None
        s = str(raw).strip()
        if s == "" or s.lower() == "nan":
            return None
        return float(s)
    except (ValueError, TypeError):
        return None


def _to_str(raw) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "" or s.lower() == "nan":
        return None
    return s


def load_records(path: str) -> List[Beneficiary]:
    """
    Load dedup_test_records.csv (or individuals_flat.csv) into normalized
    Beneficiary objects. Maps the exact column schema:

      individual_client_ref, given_name, family_name, gender, date_of_birth,
      father_name, husband_name, mobile_number, boundary_code, latitude,
      longitude, location_accuracy, locality_name, tenant_id, is_duplicate, cycle
    """
    records: List[Beneficiary] = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rec = Beneficiary(
                individual_id     = (row.get("individual_client_ref") or "").strip(),
                given_name        = _to_str(row.get("given_name")),
                family_name       = _to_str(row.get("family_name")),
                father_name       = _to_str(row.get("father_name")),
                husband_name      = _to_str(row.get("husband_name")),
                gender            = _to_str(row.get("gender")),
                date_of_birth     = _parse_date(row.get("date_of_birth")),
                boundary_code     = _to_str(row.get("boundary_code")),
                locality_name     = _to_str(row.get("locality_name")),
                latitude          = _to_float(row.get("latitude")),
                longitude         = _to_float(row.get("longitude")),
                location_accuracy = _to_float(row.get("location_accuracy")),
                mobile_number     = _to_str(row.get("mobile_number")),
                cycle             = _to_str(row.get("cycle")),
            )
            rec.normalize()
            records.append(rec)
    return records
