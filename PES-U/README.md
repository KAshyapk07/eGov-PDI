# PES-U: DIGIT HCM Projects

This folder contains project documentation, datasets, artifacts, and base project code for the PES University collaboration with eGov Foundation on the DIGIT HCM platform.

## Projects

### population-denominator-intelligence/
Satellite-based population estimation dashboard using WorldPop and Google Open Buildings data.

| Folder | Description |
|--------|-------------|
| `react/` | Base React micro-frontend module (follows health-dss pattern) |

### beneficiary-dedup-engine/
Offline-capable fuzzy matching system for detecting duplicate beneficiary registrations on mobile devices.

| Folder | Description |
|--------|-------------|
| `flutter/` | Base Flutter package (follows digit_data_converter pattern) |

### smart-grievance-mapping/
AI and GIS-enabled grievance intelligence system that converts citizen complaints into hotspot maps, severity alerts, and preventive action workflows.

## Shared Resources

### docs/
Architecture and planning documents:

| File | Description |
|------|-------------|
| `ARCHITECTURE.md` | Complete technical architecture document (17 sections) covering HLD, LLD, API contracts, database schema, GIS architecture, AI/ML pipeline, Flutter package design, and deployment strategy |
| `TASK_PLAN.md` | Detailed task breakdown into 11 independent segments (S0-S10) with acceptance criteria |
| `REQUIREMENTS.md` | Project requirements defining the capabilities (PDI + Dedup) |
| `PROJECT_OVERVIEW.html` | Product Manager-friendly project overview, printable as PDF |
| `PES-U_Project_Presentation.pptx` | PowerPoint presentation explaining the project approach, HCM data model, architecture, prerequisites, and timeline |

### synthetic_data/
Synthetic dataset (55,000 individuals) mimicking production campaign data from N'Djamena, Chad:

| File | Records | Description |
|------|---------|-------------|
| `01_schema.sql` | - | CREATE TABLE statements with indexes |
| `02_households.sql` | 11,961 | Household records with GPS |
| `03_household_addresses.sql` | 11,961 | Household addresses with boundary codes |
| `04_individuals.sql` | 55,000 | Individual records (DOB, gender, father name) |
| `05_individual_names.sql` | 55,000 | Names (givenName + familyName) |
| `06_individual_addresses.sql` | 55,000 | Individual GPS + locality |
| `07_individual_identifiers.sql` | 55,000 | Individual identifiers |
| `08_household_members.sql` | 55,000 | Household-Individual links |
| `09_project_beneficiaries.sql` | 55,000 | Campaign beneficiary records |
| `individuals_flat.csv` | 55,000 | Flat CSV export for quick analysis |
| `generate_dataset.py` | - | Python script to regenerate the dataset |
| `DATASET_README.md` | - | Detailed dataset documentation |

## Data Model

The synthetic data follows the exact HCM registration flow from `transformer_config.dart`:

```
Household (1) --< HouseholdMember >-- (N) Individual
                                           |
                                    IndividualName (givenName + familyName)
                                    IndividualAddress (GPS + boundary)
                                    IndividualIdentifier
                                           |
                                    ProjectBeneficiary --> Campaign (projectId)
```

## Quick Start

```bash
# Load into PostgreSQL
psql -d your_db -f synthetic_data/01_schema.sql
for i in 02 03 04 05 06 07 08 09; do
  psql -d your_db -f synthetic_data/${i}_*.sql
done

# Or use CSV in Python
import pandas as pd
df = pd.read_csv('synthetic_data/individuals_flat.csv')
```
