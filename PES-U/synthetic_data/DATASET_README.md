# HCM Synthetic Dataset (v2 - 55K Scale)

## Overview
Synthetic beneficiary registration data mimicking the DIGIT HCM production data model.
Data represents a Polio campaign in N'Djamena, Chad with African names
(Arabic-influenced, French-influenced, Sara/Kanuri/Hausa local names).

## Statistics
| Table | Records |
|-------|---------|
| Household | 11,961 |
| Individual | 55,000 |
| Individual Name | 55,000 |
| Individual Address | 55,000 |
| Individual Identifier | 55,000 |
| Household Member | 55,000 |
| Project Beneficiary | 55,000 |

## Data Model (from transformer_config.dart)
```
Household --< HouseholdMember >-- Individual
                                      |
                               IndividualName (givenName + familyName)
                               IndividualAddress (GPS + boundary)
                               IndividualIdentifier
                                      |
                               ProjectBeneficiary --> Campaign (projectId)
```

## Registration Flow
1. **Household** is created with GPS location and boundary assignment
2. **Individual** is registered with name (givenName + familyName), DOB, gender
3. **HouseholdMember** links the individual to the household
4. **ProjectBeneficiary** links the individual to the campaign (projectId)

## Name Characteristics
- **Arabic-influenced**: Mahamat, Ibrahim, Abubakar, Fatima, Amina, Khadija
- **French-influenced**: Jean-Pierre, Francois, Christine, Therese
- **Local/Sara/Kanuri**: Nadjitangar, Djimadoum, Ngarmbatina, Koubra
- **Hausa/Fulani**: Bukar, Modu, Bello, Garba, Shehu

## Edge Cases in Data
- **Single/short names**: Al, Ba, Ka, Ma (2-char names)
- **Compound hyphenated**: Mahamat-Saleh-Ibrahim, Jean-Baptiste-Emmanuel
- **Apostrophe names**: N'Djamena, M'Baye, N'Golo, D'Almeida
- **Gender-ambiguous**: Adama, Claude, Dominique, Ndoumbe
- **Diacritical marks**: Francois/Francois, Therese/Therese
- **Missing family names**: Some records have empty family_name

## Files
### SQL Files (execute in order)
1. `01_schema.sql` - CREATE TABLE statements with indexes
2. `02_households.sql` - Household records
3. `03_household_addresses.sql` - Household addresses with GPS
4. `04_individuals.sql` - Individual records
5. `05_individual_names.sql` - Individual names (givenName + familyName)
6. `06_individual_addresses.sql` - Individual addresses with GPS + boundary
7. `07_individual_identifiers.sql` - Individual identifiers
8. `08_household_members.sql` - Household-Individual links
9. `09_project_beneficiaries.sql` - Campaign beneficiary links

### CSV
- `individuals_flat.csv` - All individuals flattened with name, GPS, boundary

## Loading into PostgreSQL
```bash
psql -d your_db -f 01_schema.sql
for i in 02 03 04 05 06 07 08 09; do
  psql -d your_db -f ${i}_*.sql
done
```

## Loading CSV in Python
```python
import pandas as pd
individuals = pd.read_csv('individuals_flat.csv')
```

## Configuration
- Campaign: POLIO_CHAD_2024
- Region: N'Djamena, Chad
- Boundary Source: POLIO_CHAD.xlsx (45 settlement boundaries)
- GPS Center: 12.1348, 15.0557
- Seed: 42
