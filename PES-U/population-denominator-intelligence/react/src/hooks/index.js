import useAPIHook from "./useAPIHook";

/**
 * PDI Custom Hooks
 *
 * Register these hooks via Digit.Hooks so they're available globally.
 * Pattern: Digit.Hooks.pdi.usePopulationData(...)
 */

const usePopulationData = ({ tenantId, campaignId, boundaryCode, config = {} }) => {
  return useAPIHook({
    url: "/pdi/v1/_search",
    body: {
      PDISearchCriteria: {
        tenantId,
        campaignId,
        boundaryCode,
      },
    },
    params: { tenantId },
    changeQueryName: `pdi-population-${campaignId}-${boundaryCode}`,
    config,
  });
};

const useCoverageGaps = ({ tenantId, campaignId, config = {} }) => {
  return useAPIHook({
    url: "/pdi/v1/_coverage",
    body: {
      PDICoverageCriteria: {
        tenantId,
        campaignId,
      },
    },
    params: { tenantId },
    changeQueryName: `pdi-coverage-${campaignId}`,
    config,
  });
};

const hooks = {
  usePopulationData,
  useCoverageGaps,
};

export default hooks;
