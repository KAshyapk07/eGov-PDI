# DIGIT HCM - PES University Projects

This repository contains the codebase and project artifacts for **PES University** projects in collaboration with **eGov Foundation**, built on the **DIGIT Health Campaign Management (HCM)** platform.

## Projects

The repository hosts three projects for the DIGIT HCM platform used in large-scale public health campaigns (Polio vaccination, bednet distribution) across Africa:

### 1. Population Denominator Intelligence (PDI)
Satellite-based population estimation using WorldPop and Google Open Buildings data to provide accurate population counts at settlement level, enabling campaign managers to detect coverage gaps and optimize resource allocation.

### 2. Beneficiary Deduplication Engine
An offline-capable fuzzy matching system that detects duplicate beneficiary registrations on mobile devices. Uses phonetic algorithms (Soundex, Double Metaphone), string similarity (Jaro-Winkler, Levenshtein), GPS proximity scoring, and multi-attribute weighted matching to identify duplicates even when names are spelled differently across registrations.

### 3. Smart Grievance Mapping
AI and GIS-enabled grievance intelligence system that converts citizen complaints into hotspot maps, severity alerts, and preventive action workflows.

## Repository Structure

```
.
├── react/                  # DIGIT Frontend - React web application
│                           # (DIGIT HCM web modules, micro-frontend architecture)
│
├── flutter/                # Health Campaign Field Worker App - Flutter mobile application
│                           # (Offline-first mobile app used by field workers)
│                           # (Branch: merge-attendance-stock-registration)
│
├── PES-U/                  # PES University Project Artifacts & Code
│   ├── docs/               # Shared architecture docs, task plans, presentations
│   ├── synthetic_data/     # Synthetic dataset (55K records mimicking production)
│   │
│   ├── population-denominator-intelligence/
│   │   └── react/          # PDI React dashboard module (health-dss pattern)
│   │
│   ├── beneficiary-dedup-engine/
│   │   └── flutter/        # Dedup Flutter package (digit_data_converter pattern)
│   │
│   └── smart-grievance-mapping/
│       └── (project folder) # Grievance mapping project
│
└── README.md               # This file
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Mobile App | Flutter, Dart, Drift (SQLite), BLoC |
| Web Frontend | React, micro-frontend architecture |
| Backend APIs | Java Spring Boot, PostgreSQL, Kafka |
| GIS/Data | Python, PostGIS, WorldPop, Google Open Buildings |
| Infrastructure | Kubernetes, Docker, Helm |

## Getting Started

### Prerequisites
- Flutter SDK (for mobile app development)
- Node.js & Yarn (for React web frontend)
- Java 17+ & Maven (for backend services)
- PostgreSQL 14+ with PostGIS extension
- Python 3.10+ (for data processing scripts)

### Quick Start with Synthetic Data
```bash
# Load the synthetic dataset into PostgreSQL
cd PES-U/synthetic_data
psql -d your_db -f 01_schema.sql
for i in 02 03 04 05 06 07 08 09; do
  psql -d your_db -f ${i}_*.sql
done
```

## Documentation

- [Architecture Document](PES-U/docs/ARCHITECTURE.md) - Complete HLD and LLD
- [Task Plan](PES-U/docs/TASK_PLAN.md) - 11 independent work segments with acceptance criteria
- [Requirements](PES-U/docs/REQUIREMENTS.md) - Project requirements
- [Dataset Documentation](PES-U/synthetic_data/DATASET_README.md) - Synthetic data details
- [PDI React Module](PES-U/population-denominator-intelligence/react/) - PDI dashboard base project
- [Dedup Flutter Package](PES-U/beneficiary-dedup-engine/flutter/) - Dedup engine base project

## Related Repositories

- [DIGIT Frontend (upstream)](https://github.com/egovernments/DIGIT-Frontend) - React web application
- [Health Campaign Field Worker App (upstream)](https://github.com/egovernments/health-campaign-field-worker-app) - Flutter mobile app
- [DIGIT HCM Documentation](https://docs.digit.org) - Platform documentation

## License

This project is part of the DIGIT platform by eGov Foundation. See [LICENSE](react/LICENSE) for details.
