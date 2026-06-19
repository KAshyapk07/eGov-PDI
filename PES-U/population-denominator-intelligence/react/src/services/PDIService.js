import { Request } from "./CustomService";

/**
 * PDI Service - API calls for Population Denominator Intelligence.
 *
 * All endpoints follow the DIGIT API pattern:
 * - POST method with RequestInfo in body
 * - Auth token injected automatically via CustomService
 * - Tenant-aware via tenantId parameter
 */
const PDIService = {
  /**
   * Fetch population estimates for settlements in a campaign.
   *
   * Expected backend endpoint: /pdi/v1/_search
   * Expected response: { PopulationEstimates: [{ boundaryCode, estimatedPop, registeredPop, gapPercent, lat, lng }] }
   */
  search: ({ tenantId, campaignId, boundaryCode, offset = 0, limit = 100 }) =>
    Request({
      url: "/pdi/v1/_search",
      data: {
        PDISearchCriteria: {
          tenantId,
          campaignId,
          boundaryCode,
          offset,
          limit,
        },
      },
      params: { tenantId },
    }),

  /**
   * Fetch aggregated coverage gap data for a campaign.
   *
   * Expected backend endpoint: /pdi/v1/_coverage
   * Expected response: { CoverageGaps: [{ boundaryCode, settlement, estimated, registered, gap, gapPercent }] }
   */
  getCoverageGaps: ({ tenantId, campaignId }) =>
    Request({
      url: "/pdi/v1/_coverage",
      data: {
        PDICoverageCriteria: {
          tenantId,
          campaignId,
        },
      },
      params: { tenantId },
    }),
};

export default PDIService;
