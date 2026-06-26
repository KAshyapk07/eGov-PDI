"""
Generate labeled deduplication test dataset from the synthetic individuals data.

Creates known duplicate records with various transformation types, and produces:
1. dedup_test_records.csv      - Combined dataset (originals + injected duplicates)
2. dedup_ground_truth.csv      - Labels: which pairs are true duplicates and what type
3. dedup_test_summary.json     - Statistics about the test dataset

Duplicate types generated:
  - EXACT_DUPLICATE:        Identical record, different UUID (re-registration)
  - PHONETIC_VARIATION:     Arabic/French transliteration (Mahamat→Muhammad)
  - SPELLING_ERROR:         Typos - swapped/dropped/added letters
  - NAME_ABBREVIATION:      Shortened names (Ibrahim→Ibra, Jean-Pierre→Jean)
  - NAME_ORDER_SWAP:        Given/family name swapped
  - DOB_VARIATION:          Same name, slightly different DOB (transcription error)
  - GPS_NEARBY:             Same person, slightly different GPS (re-visited)
  - COMBINED_NOISE:         Multiple variations applied together (hardest case)
  - CROSS_BOUNDARY:         Same person registered in a different boundary
"""

import pandas as pd
import numpy as np
import json
import uuid
import os
import random
import copy

random.seed(42)
np.random.seed(42)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(SCRIPT_DIR, "individuals_flat.csv")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "dedup_test")

# ── Phonetic variation mappings (Arabic/French transliteration) ──────
PHONETIC_MAP = {
    # Arabic name variations common in Chad
    "Mahamat": ["Muhammad", "Mohamed", "Mohammed", "Mohamad", "Muhamat"],
    "Ibrahim": ["Ibraheem", "Ebrahim", "Brahim", "Ibrahem"],
    "Abdoulaye": ["Abdullahi", "Abdulai", "Abdulaye", "Abdoulay"],
    "Oumar": ["Omar", "Umar", "Oumare"],
    "Abakar": ["Aboubakar", "Abubakar", "Aboubacar"],
    "Youssouf": ["Yusuf", "Yousuf", "Yusef", "Youssef"],
    "Moussa": ["Musa", "Mousa", "Mussa"],
    "Issa": ["Isa", "Essa", "Eissa"],
    "Hassan": ["Hasan", "Hassane", "Hacene"],
    "Ali": ["Aly", "Ally"],
    "Fatima": ["Fatime", "Fatimatou", "Fadima", "Fadimata"],
    "Amina": ["Aminata", "Amena", "Amine"],
    "Khadija": ["Khadidja", "Kadija", "Khadijah", "Kadidja"],
    "Aisha": ["Aicha", "Aissata", "Aysha", "Aishatou"],
    "Hawa": ["Haoua", "Hauwa", "Hava"],
    "Mariam": ["Maryam", "Miriam", "Mariama", "Meriem"],
    "Djimadoum": ["Jimadoum", "Djimadoun", "Jimadoun"],
    "Nadjitangar": ["Nadjitangare", "Najitangar", "Nadjitangarre"],
    "Ngarmbatina": ["Ngarmbatinna", "Garmbatina", "Ngarmbattina"],
    # French name variations
    "Jean-Pierre": ["Jean Pierre", "Jean-Pier", "Jan-Pierre"],
    "Francois": ["Francoise", "Fransois", "Francoi"],
    "Christine": ["Kristine", "Cristine", "Kristin"],
    "Therese": ["Terese", "Theresa", "Tereze"],
    # Common family name variations
    "Deby": ["Debi", "Deby Itno", "Debby"],
    "Haroun": ["Haroune", "Haroon", "Harun"],
    "Mahamat Nour": ["Mahamad Nour", "Mohamat Nour", "Mahamatnour"],
}

# Build reverse map for lookup
PHONETIC_LOOKUP = {}
for canonical, variants in PHONETIC_MAP.items():
    PHONETIC_LOOKUP[canonical.lower()] = variants
    for v in variants:
        PHONETIC_LOOKUP[v.lower()] = [canonical] + [x for x in variants if x != v]


def add_spelling_error(name):
    """Introduce realistic spelling errors."""
    if len(name) < 3:
        return name

    error_type = random.choice(["swap", "drop", "double", "substitute"])
    chars = list(name)
    idx = random.randint(1, len(chars) - 2)  # Avoid first/last char

    if error_type == "swap" and idx < len(chars) - 1:
        chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
    elif error_type == "drop":
        chars.pop(idx)
    elif error_type == "double":
        chars.insert(idx, chars[idx])
    elif error_type == "substitute":
        similar = {
            'a': 'e', 'e': 'a', 'i': 'y', 'y': 'i', 'o': 'u', 'u': 'o',
            'b': 'p', 'p': 'b', 'd': 't', 't': 'd', 'g': 'k', 'k': 'g',
            's': 'z', 'z': 's', 'c': 'k', 'm': 'n', 'n': 'm',
        }
        c = chars[idx].lower()
        if c in similar:
            replacement = similar[c]
            chars[idx] = replacement.upper() if chars[idx].isupper() else replacement

    return "".join(chars)


def abbreviate_name(name):
    """Shorten a name realistically."""
    if "-" in name:
        # Jean-Pierre → Jean
        return name.split("-")[0]
    if " " in name:
        # Mahamat Nour → Mahamat
        return name.split(" ")[0]
    if len(name) > 5:
        # Ibrahim → Ibra, Abdoulaye → Abdou
        cut_points = [3, 4, 5]
        cut = random.choice([c for c in cut_points if c < len(name)])
        return name[:cut]
    return name


def jitter_gps(lat, lon, max_meters=80):
    """Add GPS jitter within max_meters."""
    # ~111,000 meters per degree of latitude
    lat_jitter = random.uniform(-max_meters, max_meters) / 111000
    lon_jitter = random.uniform(-max_meters, max_meters) / (111000 * np.cos(np.radians(lat)))
    return round(lat + lat_jitter, 6), round(lon + lon_jitter, 6)


def jitter_dob(dob_str):
    """Alter DOB slightly (transcription errors)."""
    from datetime import datetime, timedelta
    dob = datetime.strptime(dob_str, "%Y-%m-%d")
    error_type = random.choice(["day", "month", "year", "swap_dm"])
    if error_type == "day":
        dob += timedelta(days=random.choice([-1, 1, -2, 2]))
    elif error_type == "month":
        month = dob.month + random.choice([-1, 1])
        month = max(1, min(12, month))
        day = min(dob.day, 28)
        dob = dob.replace(month=month, day=day)
    elif error_type == "year":
        dob = dob.replace(year=dob.year + random.choice([-1, 1]))
    elif error_type == "swap_dm":
        if dob.day <= 12:
            dob = dob.replace(month=dob.day, day=dob.month)
    return dob.strftime("%Y-%m-%d")


def safe_str(val):
    """Safely convert to string, handling NaN/None."""
    if pd.isna(val):
        return ""
    return str(val)


def generate_duplicates(df):
    """Generate duplicate records with various transformation types."""
    duplicates = []
    ground_truth = []

    # Clean NaN values in name columns
    for col in ["given_name", "family_name", "father_name", "husband_name", "mobile_number"]:
        df[col] = df[col].fillna("")

    records = df.to_dict("records")
    boundary_codes = df["boundary_code"].unique().tolist()

    # ── Type 1: EXACT_DUPLICATE (5% of records = ~2750) ──
    sample = random.sample(records, min(2750, len(records)))
    for rec in sample:
        dup = copy.deepcopy(rec)
        dup["individual_client_ref"] = str(uuid.uuid4())
        dup["is_duplicate"] = True
        duplicates.append(dup)
        ground_truth.append({
            "original_id": rec["individual_client_ref"],
            "duplicate_id": dup["individual_client_ref"],
            "type": "EXACT_DUPLICATE",
            "difficulty": "EASY",
            "expected_score_min": 0.95,
            "expected_score_max": 1.0,
            "description": "Identical record, different UUID. Simulates re-registration.",
        })

    # ── Type 2: PHONETIC_VARIATION (~2000) ──
    phonetic_candidates = [r for r in records if (r["given_name"] and r["given_name"].lower() in PHONETIC_LOOKUP)
                           or (r["family_name"] and r["family_name"].lower() in PHONETIC_LOOKUP)]
    sample = random.sample(phonetic_candidates, min(2000, len(phonetic_candidates)))
    for rec in sample:
        dup = copy.deepcopy(rec)
        dup["individual_client_ref"] = str(uuid.uuid4())
        dup["is_duplicate"] = True

        # Vary given name if possible, else family name
        if rec["given_name"].lower() in PHONETIC_LOOKUP:
            variants = PHONETIC_LOOKUP[rec["given_name"].lower()]
            dup["given_name"] = random.choice(variants)
        if rec["family_name"].lower() in PHONETIC_LOOKUP and random.random() > 0.5:
            variants = PHONETIC_LOOKUP[rec["family_name"].lower()]
            dup["family_name"] = random.choice(variants)

        # Slight GPS jitter (same household, different reading)
        dup["latitude"], dup["longitude"] = jitter_gps(rec["latitude"], rec["longitude"], 30)

        duplicates.append(dup)
        ground_truth.append({
            "original_id": rec["individual_client_ref"],
            "duplicate_id": dup["individual_client_ref"],
            "type": "PHONETIC_VARIATION",
            "difficulty": "MEDIUM",
            "expected_score_min": 0.70,
            "expected_score_max": 0.95,
            "description": f"'{rec['given_name']}' → '{dup['given_name']}', "
                           f"'{rec['family_name']}' → '{dup['family_name']}'",
        })

    # ── Type 3: SPELLING_ERROR (~2000) ──
    sample = random.sample(records, min(2000, len(records)))
    for rec in sample:
        dup = copy.deepcopy(rec)
        dup["individual_client_ref"] = str(uuid.uuid4())
        dup["is_duplicate"] = True

        dup["given_name"] = add_spelling_error(rec["given_name"])
        if random.random() > 0.6:
            dup["family_name"] = add_spelling_error(rec["family_name"])

        dup["latitude"], dup["longitude"] = jitter_gps(rec["latitude"], rec["longitude"], 20)

        duplicates.append(dup)
        ground_truth.append({
            "original_id": rec["individual_client_ref"],
            "duplicate_id": dup["individual_client_ref"],
            "type": "SPELLING_ERROR",
            "difficulty": "MEDIUM",
            "expected_score_min": 0.75,
            "expected_score_max": 0.95,
            "description": f"'{rec['given_name']}' → '{dup['given_name']}', "
                           f"'{rec['family_name']}' → '{dup['family_name']}'",
        })

    # ── Type 4: NAME_ABBREVIATION (~1000) ──
    long_name_records = [r for r in records if r["given_name"] and (len(r["given_name"]) > 5 or "-" in r["given_name"])]
    sample = random.sample(long_name_records, min(1000, len(long_name_records)))
    for rec in sample:
        dup = copy.deepcopy(rec)
        dup["individual_client_ref"] = str(uuid.uuid4())
        dup["is_duplicate"] = True
        dup["given_name"] = abbreviate_name(rec["given_name"])
        dup["latitude"], dup["longitude"] = jitter_gps(rec["latitude"], rec["longitude"], 25)

        duplicates.append(dup)
        ground_truth.append({
            "original_id": rec["individual_client_ref"],
            "duplicate_id": dup["individual_client_ref"],
            "type": "NAME_ABBREVIATION",
            "difficulty": "HARD",
            "expected_score_min": 0.55,
            "expected_score_max": 0.85,
            "description": f"'{rec['given_name']}' → '{dup['given_name']}'",
        })

    # ── Type 5: NAME_ORDER_SWAP (~1000) ──
    sample = random.sample(records, min(1000, len(records)))
    for rec in sample:
        dup = copy.deepcopy(rec)
        dup["individual_client_ref"] = str(uuid.uuid4())
        dup["is_duplicate"] = True
        dup["given_name"] = rec["family_name"]
        dup["family_name"] = rec["given_name"]
        dup["latitude"], dup["longitude"] = jitter_gps(rec["latitude"], rec["longitude"], 15)

        duplicates.append(dup)
        ground_truth.append({
            "original_id": rec["individual_client_ref"],
            "duplicate_id": dup["individual_client_ref"],
            "type": "NAME_ORDER_SWAP",
            "difficulty": "MEDIUM",
            "expected_score_min": 0.65,
            "expected_score_max": 0.90,
            "description": f"'{rec['given_name']} {rec['family_name']}' → "
                           f"'{dup['given_name']} {dup['family_name']}'",
        })

    # ── Type 6: DOB_VARIATION (~1500) ──
    sample = random.sample(records, min(1500, len(records)))
    for rec in sample:
        dup = copy.deepcopy(rec)
        dup["individual_client_ref"] = str(uuid.uuid4())
        dup["is_duplicate"] = True
        dup["date_of_birth"] = jitter_dob(rec["date_of_birth"])
        # Also add minor name variation
        if random.random() > 0.5:
            dup["given_name"] = add_spelling_error(rec["given_name"])

        duplicates.append(dup)
        ground_truth.append({
            "original_id": rec["individual_client_ref"],
            "duplicate_id": dup["individual_client_ref"],
            "type": "DOB_VARIATION",
            "difficulty": "MEDIUM",
            "expected_score_min": 0.70,
            "expected_score_max": 0.95,
            "description": f"DOB '{rec['date_of_birth']}' → '{dup['date_of_birth']}'",
        })

    # ── Type 7: GPS_NEARBY (same name, different location reading) (~1000) ──
    sample = random.sample(records, min(1000, len(records)))
    for rec in sample:
        dup = copy.deepcopy(rec)
        dup["individual_client_ref"] = str(uuid.uuid4())
        dup["is_duplicate"] = True
        dup["latitude"], dup["longitude"] = jitter_gps(rec["latitude"], rec["longitude"], 150)
        dup["location_accuracy"] = round(random.uniform(10, 25), 1)

        duplicates.append(dup)
        ground_truth.append({
            "original_id": rec["individual_client_ref"],
            "duplicate_id": dup["individual_client_ref"],
            "type": "GPS_NEARBY",
            "difficulty": "EASY",
            "expected_score_min": 0.80,
            "expected_score_max": 1.0,
            "description": f"Same name, GPS shifted ~{random.randint(20, 150)}m",
        })

    # ── Type 8: COMBINED_NOISE (hardest - multiple variations) (~1500) ──
    sample = random.sample(records, min(1500, len(records)))
    for rec in sample:
        dup = copy.deepcopy(rec)
        dup["individual_client_ref"] = str(uuid.uuid4())
        dup["is_duplicate"] = True

        # Apply 2-3 variations
        transformations = []

        # Name variation
        if rec["given_name"].lower() in PHONETIC_LOOKUP and random.random() > 0.4:
            variants = PHONETIC_LOOKUP[rec["given_name"].lower()]
            dup["given_name"] = random.choice(variants)
            transformations.append("phonetic")
        else:
            dup["given_name"] = add_spelling_error(rec["given_name"])
            transformations.append("spelling")

        # Family name variation
        if random.random() > 0.5:
            dup["family_name"] = add_spelling_error(rec["family_name"])
            transformations.append("family_spelling")

        # DOB variation
        if random.random() > 0.4:
            dup["date_of_birth"] = jitter_dob(rec["date_of_birth"])
            transformations.append("dob")

        # GPS jitter (larger range)
        dup["latitude"], dup["longitude"] = jitter_gps(rec["latitude"], rec["longitude"], 200)
        transformations.append("gps")

        # Occasionally change mobile number
        if random.random() > 0.7:
            dup["mobile_number"] = ""
            transformations.append("no_phone")

        duplicates.append(dup)
        ground_truth.append({
            "original_id": rec["individual_client_ref"],
            "duplicate_id": dup["individual_client_ref"],
            "type": "COMBINED_NOISE",
            "difficulty": "HARD",
            "expected_score_min": 0.45,
            "expected_score_max": 0.85,
            "description": f"Transforms: {', '.join(transformations)}. "
                           f"'{rec['given_name']} {rec['family_name']}' → "
                           f"'{dup['given_name']} {dup['family_name']}'",
        })

    # ── Type 9: CROSS_BOUNDARY (registered in different boundary) (~750) ──
    sample = random.sample(records, min(750, len(records)))
    for rec in sample:
        dup = copy.deepcopy(rec)
        dup["individual_client_ref"] = str(uuid.uuid4())
        dup["is_duplicate"] = True

        # Move to a different nearby boundary
        other_boundaries = [b for b in boundary_codes if b != rec["boundary_code"]]
        new_boundary = random.choice(other_boundaries)
        dup["boundary_code"] = new_boundary

        # Get approximate center of new boundary from existing records
        new_boundary_recs = [r for r in records if r["boundary_code"] == new_boundary]
        if new_boundary_recs:
            ref = random.choice(new_boundary_recs)
            dup["latitude"] = ref["latitude"] + random.uniform(-0.002, 0.002)
            dup["longitude"] = ref["longitude"] + random.uniform(-0.002, 0.002)
            dup["locality_name"] = ref["locality_name"]

        # Minor name variation
        if random.random() > 0.5:
            dup["given_name"] = add_spelling_error(rec["given_name"])

        duplicates.append(dup)
        ground_truth.append({
            "original_id": rec["individual_client_ref"],
            "duplicate_id": dup["individual_client_ref"],
            "type": "CROSS_BOUNDARY",
            "difficulty": "HARD",
            "expected_score_min": 0.50,
            "expected_score_max": 0.85,
            "description": f"Boundary '{rec['locality_name']}' → '{dup['locality_name']}'",
        })

    return duplicates, ground_truth


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Loading synthetic data...")
    df = pd.read_csv(CSV_PATH)
    print(f"Original records: {len(df)}")

    print("\nGenerating labeled duplicates...")
    duplicates, ground_truth = generate_duplicates(df)

    # Mark originals
    df["is_duplicate"] = False

    # Create combined dataset
    dup_df = pd.DataFrame(duplicates)
    combined = pd.concat([df, dup_df], ignore_index=True)

    # Shuffle so duplicates aren't all at the bottom
    combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)

    # Save combined records
    records_path = os.path.join(OUTPUT_DIR, "dedup_test_records.csv")
    combined.to_csv(records_path, index=False)
    print(f"\nCombined dataset saved: {records_path}")
    print(f"  Total records: {len(combined)} ({len(df)} originals + {len(duplicates)} duplicates)")

    # Save ground truth
    gt_df = pd.DataFrame(ground_truth)
    gt_path = os.path.join(OUTPUT_DIR, "dedup_ground_truth.csv")
    gt_df.to_csv(gt_path, index=False)
    print(f"\nGround truth saved: {gt_path}")
    print(f"  Total labeled pairs: {len(gt_df)}")

    # Summary statistics
    type_counts = gt_df["type"].value_counts().to_dict()
    difficulty_counts = gt_df["difficulty"].value_counts().to_dict()

    summary = {
        "dataset": {
            "original_records": int(len(df)),
            "injected_duplicates": int(len(duplicates)),
            "total_records": int(len(combined)),
            "duplicate_ratio": round(len(duplicates) / len(combined) * 100, 1),
        },
        "duplicate_types": {k: int(v) for k, v in type_counts.items()},
        "difficulty_distribution": {k: int(v) for k, v in difficulty_counts.items()},
        "type_details": {
            "EXACT_DUPLICATE": {
                "description": "Identical record with different UUID. Simulates re-registration by same or different field worker.",
                "expected_detection": "Should be caught with >95% confidence",
                "count": int(type_counts.get("EXACT_DUPLICATE", 0)),
            },
            "PHONETIC_VARIATION": {
                "description": "Arabic/French transliteration variations (Mahamat→Muhammad, Khadija→Khadidja, Fatima→Fadima). Common in multilingual Chad context.",
                "expected_detection": "Requires Soundex/Double Metaphone to catch",
                "count": int(type_counts.get("PHONETIC_VARIATION", 0)),
            },
            "SPELLING_ERROR": {
                "description": "Typos: character swaps (Ibrahmi→Ibrahim), dropped letters (Mahamat→Mahaet), doubled letters (Khadidja→Khaddidja), substitutions (similar-sounding chars).",
                "expected_detection": "Requires Jaro-Winkler or Levenshtein with threshold tuning",
                "count": int(type_counts.get("SPELLING_ERROR", 0)),
            },
            "NAME_ABBREVIATION": {
                "description": "Shortened names: Ibrahim→Ibra, Abdoulaye→Abdou, Jean-Pierre→Jean. Common in informal registration.",
                "expected_detection": "Hardest for string similarity - needs prefix matching or containment check",
                "count": int(type_counts.get("NAME_ABBREVIATION", 0)),
            },
            "NAME_ORDER_SWAP": {
                "description": "Given and family name recorded in wrong order. E.g., 'Mahamat Deby' registered as 'Deby Mahamat'.",
                "expected_detection": "Needs cross-field comparison (compare given1 with family2 and vice versa)",
                "count": int(type_counts.get("NAME_ORDER_SWAP", 0)),
            },
            "DOB_VARIATION": {
                "description": "Date of birth transcription errors: off-by-one day/month, day-month swap (05/03→03/05), year ±1.",
                "expected_detection": "DOB fuzzy matching with ±tolerance window",
                "count": int(type_counts.get("DOB_VARIATION", 0)),
            },
            "GPS_NEARBY": {
                "description": "Identical name but GPS coordinates differ by 20-150 meters. Simulates different GPS readings at same household.",
                "expected_detection": "Haversine distance scoring should detect easily",
                "count": int(type_counts.get("GPS_NEARBY", 0)),
            },
            "COMBINED_NOISE": {
                "description": "Multiple variations applied: phonetic + spelling + DOB + GPS shift + missing phone. Simulates worst-case real-world scenario.",
                "expected_detection": "Requires multi-attribute weighted scoring to catch. Tests the full pipeline.",
                "count": int(type_counts.get("COMBINED_NOISE", 0)),
            },
            "CROSS_BOUNDARY": {
                "description": "Same person registered in a different boundary/settlement. Simulates person moving or being registered during visit to another area.",
                "expected_detection": "GPS proximity won't help here - must rely on name+DOB matching across boundaries",
                "count": int(type_counts.get("CROSS_BOUNDARY", 0)),
            },
        },
        "evaluation_guidance": {
            "metrics": [
                "Precision: Of pairs flagged as duplicates, what % are actual duplicates?",
                "Recall: Of all actual duplicate pairs, what % were detected?",
                "F1 Score: Harmonic mean of precision and recall",
            ],
            "expected_benchmarks": {
                "EASY_pairs": "Should achieve >90% recall at >90% precision",
                "MEDIUM_pairs": "Target >75% recall at >80% precision",
                "HARD_pairs": "Target >50% recall at >70% precision",
                "overall": "Target F1 > 0.75 across all types",
            },
            "usage": (
                "1. Load dedup_test_records.csv into your dedup pipeline\n"
                "2. Run the matching algorithm to produce candidate pairs with scores\n"
                "3. Compare your detected pairs against dedup_ground_truth.csv\n"
                "4. Calculate precision, recall, F1 per type and overall\n"
                "5. Tune scoring weights and thresholds to optimize F1"
            ),
        },
    }

    summary_path = os.path.join(OUTPUT_DIR, "dedup_test_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nSummary saved: {summary_path}")

    # Print summary table
    print("\n" + "=" * 65)
    print("DEDUP TEST DATASET SUMMARY")
    print("=" * 65)
    print(f"\n{'Type':<25} {'Count':>7} {'Difficulty':<10} {'Score Range'}")
    print("-" * 65)
    for t in ["EXACT_DUPLICATE", "PHONETIC_VARIATION", "SPELLING_ERROR",
              "NAME_ABBREVIATION", "NAME_ORDER_SWAP", "DOB_VARIATION",
              "GPS_NEARBY", "COMBINED_NOISE", "CROSS_BOUNDARY"]:
        info = summary["type_details"][t]
        rows = gt_df[gt_df["type"] == t]
        if len(rows) > 0:
            diff = rows["difficulty"].iloc[0]
            smin = rows["expected_score_min"].iloc[0]
            smax = rows["expected_score_max"].iloc[0]
            print(f"  {t:<23} {info['count']:>7} {diff:<10} {smin:.2f} - {smax:.2f}")

    print(f"\n{'TOTAL':<23} {len(gt_df):>9}")
    print(f"\nDifficulty breakdown:")
    for diff, count in difficulty_counts.items():
        print(f"  {diff}: {count}")


if __name__ == "__main__":
    main()
