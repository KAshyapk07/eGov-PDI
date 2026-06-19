# Getting Started Guide

This guide helps you set up the development environment and run the DIGIT HCM applications.

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Node.js | 16+ | React web frontend |
| Yarn | 1.22+ | Package manager for React |
| Flutter SDK | 3.x | Mobile app development |
| Dart | 3.4+ | Flutter's language |
| Java | 17+ | Backend services (reference only) |
| PostgreSQL | 14+ | Database + PostGIS extension |
| Python | 3.10+ | Data processing scripts |
| Git | Latest | Version control |

## Repository Setup

```bash
# Clone the repo
git clone https://github.com/egovernments/DIGIT-Frontend.git
cd DIGIT-Frontend
git checkout PES-U/project-setup
```

## Running the React Web Application

The DIGIT HCM web frontend uses a micro-frontend architecture. Each module (health-dss, campaign-manager, etc.) is a separate package.

### 1. Environment Configuration

The React app needs a DIGIT backend to connect to. Copy the env sample and configure:

```bash
cd react/health/micro-ui/web/micro-ui-internals/example
cp .env-hcm-demo .env
```

The `.env` file contains:
```
REACT_APP_PROXY_API=https://hcm-demo.digit.org    # Backend API URL
REACT_APP_PROXY_ASSETS=https://hcm-demo.digit.org  # Asset server
REACT_APP_GLOBAL=<global-config-url>                # Global JS config
REACT_APP_STATE_LEVEL_TENANT_ID=default             # Tenant ID
```

### 2. Install Dependencies and Run

```bash
cd react/health/micro-ui/web/micro-ui-internals
yarn install
yarn start
```

This starts the development server with a proxy that routes all API calls to the configured backend.

### 3. How HTTP Requests Work (React)

Every API call in DIGIT follows this pattern:

```javascript
// All POST requests include a RequestInfo object
{
  "RequestInfo": {
    "apiId": "Rainmaker",
    "authToken": "<user-access-token>",
    "userInfo": { ... },
    "msgId": "<timestamp>|<language>"
  },
  // Your actual request payload
  "YourSearchCriteria": { ... }
}
```

The `CustomService.js` in each module handles this automatically:
- Auth token is injected from `Digit.UserService.getUser().access_token`
- User info is added from the logged-in session
- Locale/language is added for i18n

**Key files to understand:**
- `health-dss/src/services/CustomService.js` - HTTP client with auth interceptors
- `health-dss/src/hooks/useAPIHook.js` - React Query wrapper for caching
- `setupProxy.js` - Dev server proxy configuration (120+ API endpoints)

## Running the Flutter Mobile App

### 1. Environment Configuration

Create a `.env` file in the Flutter app root:

```bash
cd flutter/apps/health_campaign_field_worker_app
```

Create `.env` with:
```
BASE_URL=https://hcm-demo.digit.org/
TENANT_ID=default
ENV_NAME=DEV
MDMS_API_PATH=mdms-v2/v1/_search
HIERARCHY_TYPE=ADMIN
```

### 2. Install Dependencies and Run

```bash
cd flutter
# Get dependencies for all packages
flutter pub get

cd apps/health_campaign_field_worker_app
flutter pub get
flutter run
```

### 3. How HTTP Requests Work (Flutter)

Flutter uses **Dio** HTTP client with interceptors:

```dart
// DioClient singleton (remote_client.dart)
Dio()
  ..interceptors.addAll([
    AuthTokenInterceptor(),   // Injects auth token + RequestInfo
    ApiLoggerInterceptor(),   // Logs all requests/responses
  ])
  ..options = BaseOptions(
    baseUrl: envConfig.variables.baseUrl,  // From .env file
    connectTimeout: Duration(milliseconds: 6000),
  );
```

The `AuthTokenInterceptor` automatically adds the same `RequestInfo` object to every request:

```dart
options.data = {
  ...options.data,
  "RequestInfo": {
    "apiId": "Rainmaker",
    "authToken": authToken,     // From secure storage
    "userInfo": userInfo,
    "tenantId": tenantId,
  }
};
```

**Key files to understand:**
- `lib/data/remote_client.dart` - Dio HTTP client setup
- `lib/data/repositories/api_interceptors.dart` - Auth + logging interceptors
- `lib/utils/environment_config.dart` - Env configuration loader

## Loading the Synthetic Dataset

```bash
cd PES-U/synthetic_data

# Create database and load schema
psql -d your_db -f 01_schema.sql

# Load all data files
for i in 02 03 04 05 06 07 08 09; do
  psql -d your_db -f ${i}_*.sql
done

# Verify
psql -d your_db -c "SELECT COUNT(*) FROM individual;"
# Should return: 55000
```

Or use the CSV file directly in Python:
```python
import pandas as pd
df = pd.read_csv('PES-U/synthetic_data/individuals_flat.csv')
print(f"Records: {len(df)}")  # 55000
```

## Project-Specific Setup

### PDI React Module

The base project is at `PES-U/population-denominator-intelligence/react/`.

It includes:
- `src/Module.js` - Module entry point (follows health-dss pattern)
- `src/services/CustomService.js` - HTTP client with DIGIT auth
- `src/services/PDIService.js` - PDI-specific API calls
- `src/hooks/useAPIHook.js` - React Query wrapper
- `src/hooks/index.js` - `usePopulationData` and `useCoverageGaps` hooks
- `src/components/PDICard.js` - Dashboard home card
- `src/pages/employee/` - Page routing

To integrate into the main app, this module needs to be added to the micro-ui packages and registered in the app's module initialization.

### Dedup Flutter Package

The base package is at `PES-U/beneficiary-dedup-engine/flutter/`.

It includes:
- `lib/digit_dedup_engine.dart` - Public API barrel file
- `lib/src/dedup_engine.dart` - Main orchestrator
- `lib/src/matching_service.dart` - Multi-attribute scoring
- `lib/src/blocking_strategy.dart` - Phonetic blocking
- `lib/src/algorithms/` - Soundex, Double Metaphone, Jaro-Winkler, Levenshtein stubs
- `lib/utils/gps_utils.dart` - Haversine distance (implemented)
- `lib/models/` - DedupResult, CandidatePair models

This package is designed to work **offline** on the device. It doesn't need HTTP services - it operates on local SQLite data via Drift.

## DIGIT Backend Architecture (Reference)

```
Mobile App (Flutter)
    |
    | sync (online)
    v
API Gateway (Zuul/Kong)
    |
    v
Java Spring Boot Microservices
    |
    +---> PostgreSQL (individual, household, project_beneficiary tables)
    +---> PostGIS (spatial queries for PDI)
    +---> Kafka (event streaming)
    +---> Redis (caching)
    +---> MDMS (master data management - configs, tenants, roles)
```

Students don't need to run the full backend stack locally. Point to the demo/dev environment:
- **Demo**: `https://hcm-demo.digit.org`
- **Dev**: `https://health-dev.digit.org`

These environments have the full backend running and can be used for development.
