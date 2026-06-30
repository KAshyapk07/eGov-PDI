"""
Add campaign cycle data to project_beneficiary records and flat CSV.

Real Polio campaigns in Chad run 3 cycles:
  Cycle 1 (March-April): Initial registration round
  Cycle 2 (May):         Follow-up round
  Cycle 3 (June):        Final catch-up round

Assigns cycle based on date_of_registration already in the data.
Adds 'additional_fields' JSONB column with cycle number.
Also adds cycle to the flat CSV and dedup test CSV.
"""

import os
import re
import json
import csv
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(SCRIPT_DIR, "01_schema.sql")
PB_PATH = os.path.join(SCRIPT_DIR, "09_project_beneficiaries.sql")
CSV_PATH = os.path.join(SCRIPT_DIR, "individuals_flat.csv")
DEDUP_RECORDS_PATH = os.path.join(SCRIPT_DIR, "dedup_test", "dedup_test_records.csv")


def get_cycle_from_date(date_str):
    """Assign cycle based on registration date."""
    dt = datetime.strptime(date_str.strip().strip("'"), "%Y-%m-%d %H:%M:%S")
    if dt.month <= 4:   # March-April
        return 1
    elif dt.month == 5:  # May
        return 2
    else:                # June+
        return 3


def update_schema():
    """Add additional_fields column to project_beneficiary table."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()

    # Check if already added
    if "additional_fields" in schema:
        print("Schema already has additional_fields column, skipping.")
        return

    # Add additional_fields JSONB column before row_version in project_beneficiary
    old = """    tag VARCHAR(256),
    row_version INTEGER DEFAULT 1,
    created_by VARCHAR(128) DEFAULT 'synthetic-gen',
    created_time TIMESTAMP,
    last_modified_by VARCHAR(128) DEFAULT 'synthetic-gen',
    last_modified_time TIMESTAMP
);"""

    new = """    tag VARCHAR(256),
    additional_fields JSONB DEFAULT '{}',
    row_version INTEGER DEFAULT 1,
    created_by VARCHAR(128) DEFAULT 'synthetic-gen',
    created_time TIMESTAMP,
    last_modified_by VARCHAR(128) DEFAULT 'synthetic-gen',
    last_modified_time TIMESTAMP
);"""

    schema = schema.replace(old, new)

    # Add index on cycle within additional_fields
    if "idx_pb_cycle" not in schema:
        schema += "\nCREATE INDEX idx_pb_cycle ON project_beneficiary((additional_fields->>'cycle'));\n"

    with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
        f.write(schema)

    print("Updated schema: added additional_fields JSONB column to project_beneficiary")


def update_project_beneficiaries():
    """Add additional_fields with cycle to project_beneficiary INSERT statements."""
    with open(PB_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if already updated
    if "additional_fields" in content:
        print("Project beneficiaries already have additional_fields, skipping.")
        return

    # Update header comment
    content = content.replace(
        "-- Project Beneficiaries: 55000 records",
        "-- Project Beneficiaries: 55000 records (with campaign cycle data)"
    )

    # Update INSERT column list
    old_cols = ("INSERT INTO project_beneficiary (client_reference_id, project_id, tenant_id, "
                "beneficiary_client_reference_id, date_of_registration, tag, row_version, "
                "created_time, last_modified_time) VALUES")
    new_cols = ("INSERT INTO project_beneficiary (client_reference_id, project_id, tenant_id, "
                "beneficiary_client_reference_id, date_of_registration, tag, additional_fields, "
                "row_version, created_time, last_modified_time) VALUES")

    content = content.replace(old_cols, new_cols)

    # Now process each VALUES row to inject additional_fields
    # Pattern: ('uuid', 'project', 'tenant', 'benef_uuid', 'date', NULL, 1, 'date', 'date')
    # We need to add JSON before the row_version (1)

    cycle_counts = {1: 0, 2: 0, 3: 0}

    def add_cycle_to_row(match):
        row = match.group(0)
        # Extract the date_of_registration (5th value)
        # Split carefully by comma within the VALUES tuple
        parts = row.strip().rstrip(",").rstrip(")").lstrip("(").split("'")
        # Find the date string - it's the registration date
        dates = [p.strip().strip(",").strip() for p in parts if re.match(r"\d{4}-\d{2}-\d{2}", p.strip())]
        if dates:
            date_str = dates[0]
            cycle = get_cycle_from_date(date_str)
        else:
            cycle = 1

        cycle_counts[cycle] = cycle_counts.get(cycle, 0) + 1

        # Replace "NULL, 1," with "NULL, '{"cycle":"N"}', 1,"
        cycle_json = json.dumps({"cycle": str(cycle)})
        # The pattern is: , NULL, 1, '  (tag=NULL, row_version=1)
        row = row.replace(", NULL, 1, '", f", NULL, '{cycle_json}', 1, '", 1)

        return row

    # Process line by line for reliability
    lines = content.split("\n")
    new_lines = []
    for line in lines:
        if line.strip().startswith("('") and "POLIO_CHAD" in line:
            # Extract date from the line
            date_match = re.search(r"'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'", line)
            if date_match:
                date_str = date_match.group(1)
                cycle = get_cycle_from_date(date_str)
                cycle_counts[cycle] += 1
                cycle_json = json.dumps({"cycle": str(cycle)})
                # Replace: NULL, 1, 'date' with: NULL, '{"cycle":"N"}', 1, 'date'
                # Find the pattern: , NULL, 1, ' (after tag, before created_time)
                line = line.replace(", NULL, 1, '", f", NULL, '{cycle_json}', 1, '", 1)
            new_lines.append(line)
        else:
            new_lines.append(line)

    content = "\n".join(new_lines)

    with open(PB_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Updated project_beneficiaries with cycle data:")
    print(f"  Cycle 1 (Mar-Apr): {cycle_counts[1]} records")
    print(f"  Cycle 2 (May):     {cycle_counts[2]} records")
    print(f"  Cycle 3 (Jun):     {cycle_counts[3]} records")
    print(f"  Total:             {sum(cycle_counts.values())} records")


def update_flat_csv():
    """Add cycle column to the flat CSV based on date ranges in project_beneficiary."""
    # Since the flat CSV doesn't have date_of_registration directly,
    # we need to read the project_beneficiary SQL to get the mapping
    # beneficiary_client_reference_id -> date -> cycle

    # Build mapping from the SQL file
    benef_cycle = {}
    with open(PB_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip().startswith("('"):
                continue
            # Extract beneficiary_client_reference_id and date
            parts = line.split("'")
            # UUID positions: [1]=client_ref, [3]=project_id, [5]=tenant, [7]=benef_ref, [9]=date
            if len(parts) >= 10:
                benef_ref = parts[7]
                date_str = parts[9]
                if re.match(r"\d{4}-\d{2}-\d{2}", date_str):
                    cycle = get_cycle_from_date(date_str)
                    benef_cycle[benef_ref] = cycle

    print(f"\nBuilt cycle mapping for {len(benef_cycle)} beneficiaries")

    # Update flat CSV
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames

        # Add cycle column if not present
        if "cycle" not in fieldnames:
            fieldnames = fieldnames + ["cycle"]

        for row in rows:
            ref = row.get("individual_client_ref", "")
            row["cycle"] = str(benef_cycle.get(ref, 1))

        with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        cycle_dist = {}
        for row in rows:
            c = row["cycle"]
            cycle_dist[c] = cycle_dist.get(c, 0) + 1
        print(f"Updated {CSV_PATH}")
        print(f"  Cycle distribution: {cycle_dist}")

    # Update dedup test CSV if it exists
    if os.path.exists(DEDUP_RECORDS_PATH):
        with open(DEDUP_RECORDS_PATH, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames

        if "cycle" not in fieldnames:
            fieldnames = fieldnames + ["cycle"]

        for row in rows:
            ref = row.get("individual_client_ref", "")
            # For duplicates (injected), assign a random cycle (often different from original)
            if row.get("is_duplicate") == "True" and ref not in benef_cycle:
                row["cycle"] = str(random.choice([1, 2, 3]))
            else:
                row["cycle"] = str(benef_cycle.get(ref, 1))

        with open(DEDUP_RECORDS_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"Updated dedup test records with cycle data")


import random
random.seed(42)


def main():
    print("=" * 60)
    print("ADDING CAMPAIGN CYCLE DATA")
    print("=" * 60)
    print("\nCampaign: POLIO_CHAD_2024 (3 cycles)")
    print("  Cycle 1: March-April 2024 (Initial round)")
    print("  Cycle 2: May 2024 (Follow-up round)")
    print("  Cycle 3: June 2024 (Final catch-up round)")

    print("\n--- Step 1: Update schema ---")
    update_schema()

    print("\n--- Step 2: Update project_beneficiary SQL ---")
    update_project_beneficiaries()

    print("\n--- Step 3: Update flat CSV and dedup test CSV ---")
    update_flat_csv()

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
