import { CustomService } from "../services/CustomService";
import { useQuery, useQueryClient } from "react-query";
import { useMemo } from "react";

/**
 * Generic API hook for PDI module.
 * Wraps CustomService with React Query for caching and state management.
 *
 * Usage:
 *   const { isLoading, data, refetch } = useAPIHook({
 *     url: "/pdi/v1/_search",
 *     body: { boundaryCode: "WALIA_EST" },
 *     changeQueryName: "pdi-search",
 *   });
 */
const useAPIHook = ({
  url,
  params = {},
  body = {},
  config = {},
  headers = {},
  method = "POST",
  changeQueryName = "Random",
  options = {},
}) => {
  const client = useQueryClient();

  const stableBody = useMemo(() => JSON.stringify(body), [body]);
  const queryKey = useMemo(() => [url, changeQueryName, stableBody], [url, changeQueryName, stableBody]);

  const fetchData = async () => {
    const response = await CustomService.getResponse({ url, params, body, headers, method, ...options });
    return response || null;
  };

  const { isLoading, data, isFetching, refetch } = useQuery(queryKey, fetchData, {
    cacheTime: options?.cacheTime || 1000,
    staleTime: options?.staleTime || 5000,
    keepPreviousData: true,
    retry: 2,
    refetchOnWindowFocus: false,
    ...config,
  });

  return {
    isLoading,
    isFetching,
    data,
    refetch,
    revalidate: () => {
      if (data) {
        client.invalidateQueries(queryKey);
      }
    },
  };
};

export default useAPIHook;
