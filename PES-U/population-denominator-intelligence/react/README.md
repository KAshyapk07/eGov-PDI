# Population Denominator Intelligence (PDI) - React Module

DIGIT HCM micro-frontend module for Population Denominator Intelligence dashboard.

## Overview

Provides a dashboard for campaign managers to view satellite-based population estimates at settlement level, compare against registered beneficiary counts, and identify coverage gaps.

## Module Structure

```
src/
  Module.js           - Entry point, exports PDIModule and initPDIComponents
  components/         - Reusable UI components (charts, maps, cards)
  pages/employee/     - Page-level components with routing
  hooks/              - Custom React hooks for data fetching
  services/           - API service layer (PostGIS backend calls)
  configs/            - UI customization configurations
  utils/              - Utility functions
```

## Pattern

This module follows the same pattern as `@egovernments/digit-ui-module-health-dss`. See the health-dss module in `react/health/micro-ui/web/micro-ui-internals/packages/modules/health-dss/` for reference.

## Development

```bash
yarn install
yarn start   # Watch mode for development
yarn build   # Production build
```
