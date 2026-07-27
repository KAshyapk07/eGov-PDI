import { useState } from "react";
import { COUNTRIES, countryLabel } from "./countries.js";

const DEFAULT_YEAR = 2026;
const campaignFor = (iso3, year) => `PDI-${iso3}-${year}`;

export default function InputsPanel({ onCompute, error }) {
  const [iso3, setIso3] = useState("TCD");
  const [year, setYear] = useState(DEFAULT_YEAR);
  const [sheet, setSheet] = useState(null);
  const [householdSize, setHouseholdSize] = useState("");
  const [tenantId, setTenantId] = useState("default");
  const [campaignId, setCampaignId] = useState("");

  // The campaign id defaults to PDI-<ISO3>-<YEAR> but stays editable; this is the
  // key the results dashboard reads back from the persisted tables.
  const resolvedCampaign = campaignId.trim() || campaignFor(iso3, year);

  const run = (force) => onCompute({
    iso3,
    year,
    sheet,
    householdSize: householdSize ? Number(householdSize) : undefined,
    withBuildings: true,
    campaignId: resolvedCampaign,
    tenantId: tenantId.trim() || "default",
    force,
  });

  const submit = (event) => {
    event.preventDefault();
    run(false);
  };

  return (
    <section className="compute-panel">
      <div className="compute-panel-head">
        <h2>Compute campaign targets</h2>
        <p>
          Pick a country and, optionally, a microplan boundary sheet. The engine returns
          per-boundary household and age-group targets from WorldPop population and VIDA building
          footprints.
        </p>
      </div>

      <form className="compute-form" onSubmit={submit}>
        <div className="field-row">
          <label className="field field-grow">
            <span className="field-label">Country</span>
            <select
              className="field-input"
              value={iso3}
              onChange={(event) => setIso3(event.target.value)}
            >
              {COUNTRIES.map((country) => (
                <option key={country.iso3} value={country.iso3}>{countryLabel(country)}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="field-label">WorldPop year</span>
            <input
              type="number"
              step="1"
              min="2000"
              max="2030"
              className="field-input year-input"
              value={year}
              onChange={(event) => setYear(Number(event.target.value))}
            />
          </label>
        </div>

        <label className="field">
          <span className="field-label">Boundary sheet <em>optional</em></span>
          <input
            type="file"
            accept=".xlsx"
            className="field-file"
            onChange={(event) => setSheet(event.target.files?.[0] ?? null)}
          />
          <span className="field-hint">
            {sheet
              ? `Selected: ${sheet.name} — adds a Voronoi catchment layer per service point.`
              : "The whole country is always computed by district. Add a sheet to also get a Voronoi catchment layer, one cell per health centre, with buildings mapped to their nearest centre."}
          </span>
        </label>

        <label className="field">
          <span className="field-label">Avg household size <em>optional</em></span>
          <input
            type="number"
            step="0.1"
            min="1"
            className="field-input"
            value={householdSize}
            onChange={(event) => setHouseholdSize(event.target.value)}
            placeholder="country default"
          />
          <span className="field-hint">
            You can re-tune this on the results screen and every estimate updates instantly — no
            re-run needed.
          </span>
        </label>

        <div className="field-row">
          <label className="field field-grow">
            <span className="field-label">Campaign ID <em>optional</em></span>
            <input
              type="text"
              className="field-input"
              value={campaignId}
              onChange={(event) => setCampaignId(event.target.value)}
              placeholder={campaignFor(iso3, year)}
            />
          </label>
          <label className="field">
            <span className="field-label">Tenant</span>
            <input
              type="text"
              className="field-input tenant-input"
              value={tenantId}
              onChange={(event) => setTenantId(event.target.value)}
            />
          </label>
        </div>

        {error && <div className="input-error">{error}</div>}

        <div className="compute-actions">
          <button className="cta" type="submit" disabled={!iso3}>Compute targets</button>
          <button
            className="cta cta-secondary"
            type="button"
            disabled={!iso3}
            onClick={() => run(true)}
          >
            Recompute
          </button>
        </div>

        <p className="compute-note">
          The first run for a country downloads WorldPop rasters (~1&ndash;2&nbsp;GB) and can take a
          few minutes; later runs are served from the stored result.{" "}
          <strong>Recompute</strong> ignores the stored result, re-runs the engine for these exact
          settings and overwrites what is saved &mdash; use it when the underlying data has changed.
        </p>
      </form>
    </section>
  );
}
