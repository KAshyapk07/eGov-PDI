import { fmtInt, fmtPct } from "../lib/format.js";

// Renders the documented dashboard summary (ARCHITECTURE.md §14.2) served from the
// pre-computed PostGIS tables via GET /population/v1/dashboard/_stats. When stats is
// null the campaign has not been persisted (database off during compute) and the
// map-driven views carry the demo on their own.
export default function DashboardSummary({ stats }) {
  if (!stats) return null;
  const s = stats.summary;

  const tiles = [
    { k: "Estimated population", v: fmtInt(s.totalEstimatedPopulation) },
    { k: "Registered population", v: fmtInt(s.totalRegisteredPopulation) },
    { k: "Population gap", v: fmtInt(s.totalPopulationGap) },
    { k: "Coverage", v: s.overallCoverageRatio != null ? fmtPct(s.overallCoverageRatio, 1) : "—" },
    { k: "Estimated households", v: fmtInt(s.totalEstimatedHouseholds) },
    { k: "Household gap", v: fmtInt(s.householdGap) },
    { k: "Invisible settlements", v: fmtInt(s.invisibleSettlementCount) },
    { k: "Invisible population", v: fmtInt(s.invisibleEstimatedPopulation) },
  ];

  const gapClasses = Object.entries(stats.gapDistribution || {});
  const riskClasses = Object.entries(stats.riskDistribution || {});

  return (
    <section className="dash">
      <div className="dash-head">
        <span className="dash-title">Campaign summary</span>
        <span className="dash-src mono">/population/v1/dashboard/_stats · PostGIS</span>
      </div>
      <div className="dash-tiles">
        {tiles.map((t) => (
          <div className="dash-tile" key={t.k}>
            <div className="dash-tile-v num">{t.v}</div>
            <div className="dash-tile-k">{t.k}</div>
          </div>
        ))}
      </div>
      {(gapClasses.length > 0 || riskClasses.length > 0) && (
        <div className="dash-dists">
          {gapClasses.length > 0 && (
            <div className="dash-dist">
              <span className="dash-dist-k">Gap classification</span>
              <div className="dash-chips">
                {gapClasses.map(([name, bucket]) => (
                  <span className={`chip gap-${name.toLowerCase()}`} key={name}>
                    {name} · {fmtInt(bucket.count)}
                  </span>
                ))}
              </div>
            </div>
          )}
          {riskClasses.length > 0 && (
            <div className="dash-dist">
              <span className="dash-dist-k">Risk priority</span>
              <div className="dash-chips">
                {riskClasses.map(([name, count]) => (
                  <span className={`chip risk-${name.toLowerCase()}`} key={name}>
                    {name} · {fmtInt(count)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
