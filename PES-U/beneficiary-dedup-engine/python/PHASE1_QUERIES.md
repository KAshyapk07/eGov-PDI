# Phase 1 — SQL Query Documentation

How the dedup engine's flat record is reconstructed from the relational HCM
schema. The engine is unchanged; only the data source moved from CSV to SQL.

## Data model (relevant tables)

The engine scores one **individual** at a time. In the CSV, all fields sat in
one row. In SQL they are spread across five tables, all one-to-one in this
dataset (verified: 55,000 rows each, 55,000 distinct individuals):

| Field the engine needs | Source table          | Column                              |
|------------------------|-----------------------|-------------------------------------|
| individual id          | `individual`          | `client_reference_id`               |
| given_name             | `individual_name`     | `given_name`                        |
| family_name            | `individual_name`     | `family_name`                       |
| gender                 | `individual`          | `gender`                            |
| date_of_birth          | `individual`          | `date_of_birth`                     |
| father_name            | `individual`          | `father_name`                       |
| husband_name           | `individual`          | `husband_name`                      |
| mobile_number          | `individual`          | `mobile_number`                     |
| boundary_code          | `individual`          | `boundary_code`                     |
| latitude               | `individual_address`  | `latitude`                          |
| longitude              | `individual_address`  | `longitude`                         |
| location_accuracy      | `individual_address`  | `location_accuracy`                 |
| locality_name          | `individual_address`  | `locality_name`                     |
| tenant_id              | `individual`          | `tenant_id`                         |
| cycle                  | `project_beneficiary` | `additional_fields->>'cycle'` (JSON)|

`household`, `household_address`, `household_member`, and `individual_identifier`
are **not used** by the current engine (individual-level dedup only).

## Join keys

- `individual_name.individual_client_reference_id`  ->  `individual.client_reference_id`
- `individual_address.related_client_reference_id`  ->  `individual.client_reference_id`
- `project_beneficiary.beneficiary_client_reference_id`  ->  `individual.client_reference_id`

All three verified to join cleanly (55,000 matches each).

## Cycle extraction (the one non-obvious part)

Cycle is not a column — it lives inside `project_beneficiary.additional_fields`,
a JSON/JSONB blob. In PostgreSQL:

```sql
pb.additional_fields->>'cycle'
```

In SQLite (Phase 2 / on-device) the equivalent is:

```sql
json_extract(pb.additional_fields, '$.cycle')
```

This is the only query line that differs between Postgres and SQLite; the rest
of the joins are identical.

Cycle distribution in this dataset: cycle 1 = 27,321, cycle 2 = 14,104,
cycle 3 = 13,575. Each individual belongs to exactly one cycle.

## Full fetch query (PostgreSQL)

```sql
SELECT
    i.client_reference_id            AS individual_client_ref,
    n.given_name,
    n.family_name,
    i.gender,
    i.date_of_birth,
    i.father_name,
    i.husband_name,
    i.mobile_number,
    i.boundary_code,
    a.latitude,
    a.longitude,
    a.location_accuracy,
    a.locality_name,
    i.tenant_id,
    pb.additional_fields->>'cycle'   AS cycle
FROM individual i
JOIN individual_name n
    ON n.individual_client_reference_id = i.client_reference_id
LEFT JOIN individual_address a
    ON a.related_client_reference_id = i.client_reference_id
LEFT JOIN project_beneficiary pb
    ON pb.beneficiary_client_reference_id = i.client_reference_id;
```

`JOIN` on name (every individual has exactly one). `LEFT JOIN` on address and
beneficiary so a missing row never silently drops an individual.

## On-device query pattern (Phase 2 preview)

On the phone the engine does NOT load all rows and loop. For one new record it
issues a narrow blocking query — the SQL equivalent of the Python blocking
rules — for example candidates in the same boundary, or the same birth year:

```sql
-- candidates worth scoring against a new record
SELECT ... (same joins as above) ...
WHERE i.boundary_code = :boundary
   OR i.date_of_birth BETWEEN :dob_lo AND :dob_hi;
```

The indexes already present (`idx_ind_boundary`, `idx_ind_dob`,
`idx_ind_name_given`, `idx_pb_cycle`) support exactly these lookups.
```
