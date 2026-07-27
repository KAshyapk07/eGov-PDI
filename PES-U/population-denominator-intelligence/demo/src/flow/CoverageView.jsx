import { useMemo, useState } from "react";
import CoverageMap from "./CoverageMap.jsx";
import { classCounts, gapMeta } from "../lib/gap.js";
import { fmtInt, fmtPct } from "../lib/format.js";
import { IconMap } from "../components/icons.jsx";

const nameOf = (p) => p.name || p.boundaryCode;

// Coverage tab for the live API run. Every field is read straight from the
// units.geojson the engine now enriches with the registered denominator:
// registered_population/under5/households, coverage_ratio and gap_classification.
export default function CoverageView({ geojson, downloadUrl }) {
  const [selected, setSelected] = useState(null);
  const [active, setActive] = useState(null);

  const { counts, kpis } = useMemo(() => {
    let estimated = 0;
    let registered = 0;
    let covered = 0;
    let blackPop = 0;
    for (const f of geojson.features) {
      const p = f.properties;
      estimated += Number(p.population_estimate) || 0;
      registered += Number(p.registered_population) || 0;
      if (Number(p.registered_population) > 0) covered += 1;
      if (p.gap_classification === "BLACK") blackPop += Number(p.population_estimate) || 0;
    }
    const c = classCounts(geojson.features);
    const gap = estimated - registered;
    return {
      counts: c,
      kpis: [
        { k: "Estimated population", v: fmtInt(estimated), s: `${geojson.features.length} boundaries`, bar: "var(--primary)" },
        { k: "Registered", v: fmtInt(registered), s: `${covered} boundaries covered`, bar: "var(--secondary)" },
        { k: "Coverage gap", v: fmtInt(gap), s: `${fmtPct(estimated ? gap / estimated : 0, 1)} unregistered`, bar: gapMeta("RED").color },
        { k: "Never reached", v: `${c.BLACK}`, s: `${fmtInt(blackPop)} people, built-up but unregistered`, bar: gapMeta("BLACK").color },
      ],
    };
  }, [geojson]);

  return (
    <div className="results-scroll cov-view">
      <div className="cov-kpis">
        {kpis.map((c) => (
          <div className="cov-kpi" key={c.k} style={{ "--accent-bar": c.bar }}>
            <div className="cov-kpi-k">{c.k}</div>
            <div className="cov-kpi-v num">{c.v}</div>
            <div className="cov-kpi-s">{c.s}</div>
          </div>
        ))}
      </div>
      <div className="split results-split-map">
        <CoverageMap
          geojson={geojson}
          counts={counts}
          active={active}
          setActive={setActive}
          onSelect={setSelected}
          selectedCode={selected?.boundaryCode}
          downloadUrl={downloadUrl}
        />
        <CoveragePanel props={selected} />
      </div>
    </div>
  );
}

function CoverageBar({ label, registered, estimated, color }) {
  const pct = estimated > 0 ? Math.min(registered / estimated, 1) : 0;
  return (
    <div className="cov-bar">
      <div className="cov-bar-head">
        <span>{label}</span>
        <span className="num">{fmtInt(registered)} / {fmtInt(estimated)}</span>
      </div>
      <div className="cov-track">
        <span className="cov-fill" style={{ width: `${pct * 100}%`, background: color }} />
      </div>
    </div>
  );
}

function Metric({ k, v }) {
  return (
    <div className="metric">
      <div className="k">{k}</div>
      <div className="v num">{v}</div>
    </div>
  );
}

function CoveragePanel({ props }) {
  if (!props) {
    return (
      <div className="panel">
        <div className="empty">
          <IconMap />
          <div>Select a boundary on the map to see its coverage gap, or click a class in the legend to filter.</div>
        </div>
      </div>
    );
  }

  const meta = gapMeta(props.gap_classification);
  const registered = Number(props.registered_population) || 0;
  const estimated = Number(props.population_estimate) || 0;
  const registeredU5 = Number(props.registered_under5) || 0;
  const estimatedU5 = Math.round(Number(props.under5) || 0);
  const coverage = Number(props.coverage_ratio);
  const coverageU5 = Number(props.coverage_ratio_under5);
  const neverReached = props.gap_classification === "BLACK";

  return (
    <div className="panel">
      <h2>{nameOf(props)}</h2>
      <div className="sub mono">{props.boundaryCode}</div>
      {props.is_catchment ? <span className="badge">catchment cell</span> : null}

      <div className="cov-hero" style={{ "--cls": meta.color }}>
        <div className="cov-hero-top">
          <span className="pill" style={{ background: meta.color }}>
            <span className="dot" />{meta.label}
          </span>
          <span className="cov-hero-pct num">
            {registered > 0 ? fmtPct(coverage, 1) : "0%"}
          </span>
        </div>
        <div className="cov-hero-sub">
          {neverReached
            ? `No one registered here — an estimated ${fmtInt(estimated)} people the campaign never reached.`
            : `${fmtInt(registered)} registered of an estimated ${fmtInt(estimated)}.`}
        </div>
      </div>

      <div className="section-title">Population coverage</div>
      <CoverageBar label="All ages" registered={registered} estimated={estimated} color={meta.color} />
      <CoverageBar label="Under-5" registered={registeredU5} estimated={estimatedU5} color={meta.color} />

      <div className="section-title">Gap</div>
      <div className="metric-grid">
        <Metric k="Population gap" v={fmtInt(estimated - registered)} />
        <Metric k="Registered" v={fmtInt(registered)} />
        <Metric k="Estimated" v={fmtInt(estimated)} />
        <Metric k="Under-5 coverage" v={registered > 0 ? fmtPct(coverageU5, 1) : "0%"} />
        <Metric k="Reg. households" v={fmtInt(props.registered_households)} />
        <Metric k="Buildings" v={fmtInt(props.building_count)} />
      </div>
    </div>
  );
}
