const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8080";

export const absoluteUrl = (path) => `${BASE}${path}`;

// `force` bypasses the stored result and re-runs the engine, overwriting the cache
// entry for these exact parameters. Everything else identifies the result itself.
export async function submitCompute({
  iso3, year, sheet, householdSize, groups, withBuildings, campaignId, tenantId, force,
}) {
  const form = new FormData();
  form.append("iso3", iso3);
  if (year) form.append("year", String(year));
  if (sheet) form.append("sheet", sheet);
  if (householdSize) form.append("householdSize", String(householdSize));
  if (groups) form.append("groups", groups);
  form.append("withBuildings", String(withBuildings));
  if (campaignId) form.append("campaignId", campaignId);
  if (tenantId) form.append("tenantId", tenantId);
  if (force) form.append("force", "true");

  let response;
  try {
    response = await fetch(`${BASE}/population/v1/targets/_compute`, {
      method: "POST",
      body: form,
    });
  } catch (networkError) {
    throw new Error(`Could not reach the engine at ${BASE}. Is the API running?`);
  }
  if (!response.ok) {
    throw new Error(await problemDetail(response, "The engine rejected the request"));
  }
  return response.json();
}

export async function fetchStatus(statusUrl) {
  const response = await fetch(absoluteUrl(statusUrl));
  if (!response.ok) {
    throw new Error(await problemDetail(response, "Status check failed"));
  }
  return response.json();
}

export async function fetchGeojson(path) {
  const response = await fetch(absoluteUrl(path));
  if (!response.ok) throw new Error("Could not load the boundary geometry.");
  return response.json();
}

// Documented read endpoint (ARCHITECTURE.md §14.2): the dashboard summary served
// from the pre-computed PostGIS tables. Returns null if the campaign has not been
// persisted (e.g. the database was unreachable during compute), so the map-driven
// views still render.
export async function fetchDashboardStats({ campaignId, boundaryCode, tenantId }) {
  const params = new URLSearchParams({ campaignId, tenantId: tenantId || "default" });
  if (boundaryCode) params.set("boundaryCode", boundaryCode);
  try {
    const response = await fetch(`${BASE}/population/v1/dashboard/_stats?${params}`);
    if (!response.ok) return null;
    const stats = await response.json();
    return stats?.summary?.totalEstimatedPopulation ? stats : null;
  } catch (ignored) {
    return null;
  }
}

async function problemDetail(response, fallback) {
  try {
    const problem = await response.json();
    if (problem.detail) return problem.detail;
  } catch (ignored) {
    // no JSON body
  }
  return `${fallback} (${response.status}).`;
}
