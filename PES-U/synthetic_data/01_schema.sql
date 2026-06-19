-- ============================================================
-- HCM Synthetic Dataset - Schema (v2 - 55K Scale)
-- Matches transformer_config.dart data model
-- ============================================================

DROP TABLE IF EXISTS project_beneficiary CASCADE;
DROP TABLE IF EXISTS household_member CASCADE;
DROP TABLE IF EXISTS individual_identifier CASCADE;
DROP TABLE IF EXISTS individual_address CASCADE;
DROP TABLE IF EXISTS individual_name CASCADE;
DROP TABLE IF EXISTS individual CASCADE;
DROP TABLE IF EXISTS household_address CASCADE;
DROP TABLE IF EXISTS household CASCADE;

CREATE TABLE household (
    id SERIAL PRIMARY KEY,
    client_reference_id UUID NOT NULL UNIQUE,
    member_count INTEGER DEFAULT 1,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    tenant_id VARCHAR(64) NOT NULL,
    row_version INTEGER DEFAULT 1,
    household_type VARCHAR(32) DEFAULT 'FAMILY',
    children_count INTEGER DEFAULT 0,
    pregnant_women_count INTEGER DEFAULT 0,
    created_by VARCHAR(128) DEFAULT 'synthetic-gen',
    created_time TIMESTAMP,
    last_modified_by VARCHAR(128) DEFAULT 'synthetic-gen',
    last_modified_time TIMESTAMP
);

CREATE TABLE household_address (
    id SERIAL PRIMARY KEY,
    client_reference_id UUID NOT NULL UNIQUE,
    related_client_reference_id UUID NOT NULL REFERENCES household(client_reference_id),
    door_no VARCHAR(32),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    location_accuracy DOUBLE PRECISION,
    address_line1 TEXT,
    address_line2 TEXT,
    type VARCHAR(32) DEFAULT 'PERMANENT',
    locality_code VARCHAR(256),
    locality_name VARCHAR(256),
    tenant_id VARCHAR(64) NOT NULL,
    row_version INTEGER DEFAULT 1,
    created_by VARCHAR(128) DEFAULT 'synthetic-gen',
    created_time TIMESTAMP,
    last_modified_by VARCHAR(128) DEFAULT 'synthetic-gen',
    last_modified_time TIMESTAMP
);

CREATE TABLE individual (
    id SERIAL PRIMARY KEY,
    client_reference_id UUID NOT NULL UNIQUE,
    date_of_birth DATE,
    mobile_number VARCHAR(32),
    father_name VARCHAR(256),
    husband_name VARCHAR(256),
    gender VARCHAR(16),
    boundary_code VARCHAR(256),
    tenant_id VARCHAR(64) NOT NULL,
    row_version INTEGER DEFAULT 1,
    created_by VARCHAR(128) DEFAULT 'synthetic-gen',
    created_time TIMESTAMP,
    last_modified_by VARCHAR(128) DEFAULT 'synthetic-gen',
    last_modified_time TIMESTAMP
);

CREATE TABLE individual_name (
    id SERIAL PRIMARY KEY,
    client_reference_id UUID NOT NULL UNIQUE,
    individual_client_reference_id UUID NOT NULL REFERENCES individual(client_reference_id),
    given_name VARCHAR(256) NOT NULL,
    family_name VARCHAR(256),
    tenant_id VARCHAR(64) NOT NULL,
    row_version INTEGER DEFAULT 1,
    created_by VARCHAR(128) DEFAULT 'synthetic-gen',
    created_time TIMESTAMP
);

CREATE TABLE individual_address (
    id SERIAL PRIMARY KEY,
    client_reference_id UUID NOT NULL UNIQUE,
    related_client_reference_id UUID NOT NULL REFERENCES individual(client_reference_id),
    door_no VARCHAR(32),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    location_accuracy DOUBLE PRECISION,
    address_line1 TEXT,
    address_line2 TEXT,
    type VARCHAR(32) DEFAULT 'PERMANENT',
    locality_code VARCHAR(256),
    locality_name VARCHAR(256),
    tenant_id VARCHAR(64) NOT NULL,
    row_version INTEGER DEFAULT 1,
    created_by VARCHAR(128) DEFAULT 'synthetic-gen',
    created_time TIMESTAMP,
    last_modified_by VARCHAR(128) DEFAULT 'synthetic-gen',
    last_modified_time TIMESTAMP
);

CREATE TABLE individual_identifier (
    id SERIAL PRIMARY KEY,
    client_reference_id UUID NOT NULL UNIQUE,
    individual_client_reference_id UUID NOT NULL REFERENCES individual(client_reference_id),
    identifier_type VARCHAR(64),
    identifier_id VARCHAR(256),
    boundary_code VARCHAR(256),
    tenant_id VARCHAR(64) NOT NULL,
    row_version INTEGER DEFAULT 1,
    created_by VARCHAR(128) DEFAULT 'synthetic-gen',
    created_time TIMESTAMP
);

CREATE TABLE household_member (
    id SERIAL PRIMARY KEY,
    client_reference_id UUID NOT NULL UNIQUE,
    household_client_reference_id UUID NOT NULL REFERENCES household(client_reference_id),
    individual_client_reference_id UUID NOT NULL REFERENCES individual(client_reference_id),
    is_head_of_household BOOLEAN DEFAULT FALSE,
    tenant_id VARCHAR(64) NOT NULL,
    row_version INTEGER DEFAULT 1,
    created_by VARCHAR(128) DEFAULT 'synthetic-gen',
    created_time TIMESTAMP,
    last_modified_by VARCHAR(128) DEFAULT 'synthetic-gen',
    last_modified_time TIMESTAMP
);

CREATE TABLE project_beneficiary (
    id SERIAL PRIMARY KEY,
    client_reference_id UUID NOT NULL UNIQUE,
    project_id VARCHAR(128) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    beneficiary_client_reference_id UUID NOT NULL,
    date_of_registration TIMESTAMP,
    tag VARCHAR(256),
    row_version INTEGER DEFAULT 1,
    created_by VARCHAR(128) DEFAULT 'synthetic-gen',
    created_time TIMESTAMP,
    last_modified_by VARCHAR(128) DEFAULT 'synthetic-gen',
    last_modified_time TIMESTAMP
);

-- Performance indexes
CREATE INDEX idx_ind_name_given ON individual_name(given_name);
CREATE INDEX idx_ind_name_family ON individual_name(family_name);
CREATE INDEX idx_ind_gender ON individual(gender);
CREATE INDEX idx_ind_boundary ON individual(boundary_code);
CREATE INDEX idx_ind_dob ON individual(date_of_birth);
CREATE INDEX idx_ind_father ON individual(father_name);
CREATE INDEX idx_hm_hh ON household_member(household_client_reference_id);
CREATE INDEX idx_hm_ind ON household_member(individual_client_reference_id);
CREATE INDEX idx_pb_benef ON project_beneficiary(beneficiary_client_reference_id);
CREATE INDEX idx_pb_project ON project_beneficiary(project_id);
CREATE INDEX idx_ind_addr_loc ON individual_address(locality_code);
