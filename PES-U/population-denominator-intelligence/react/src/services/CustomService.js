import Axios from "axios";

/**
 * Custom HTTP Request handler for PDI module.
 * Follows the same pattern as health-dss CustomService.
 *
 * All DIGIT API calls require a RequestInfo object in POST body
 * containing apiId, authToken, userInfo, and locale.
 */

Axios.interceptors.response.use(
  (res) => res,
  (err) => {
    const isEmployee = window.location.pathname.split("/").includes("employee");
    if (err?.response?.data?.Errors) {
      for (const error of err.response.data.Errors) {
        if (error.message.includes("InvalidAccessTokenException")) {
          localStorage.clear();
          sessionStorage.clear();
          window.location.href =
            (isEmployee ? `/${window?.contextPath}/employee/user/login` : `/${window?.contextPath}/citizen/login`) +
            `?from=${encodeURIComponent(window.location.pathname + window.location.search)}`;
        }
      }
    }
    throw err;
  }
);

const requestInfo = () => ({
  authToken: Digit.UserService.getUser()?.access_token || null,
});

const userServiceData = () => ({ userInfo: Digit.UserService.getUser()?.info });

export const Request = async ({
  method = "POST",
  url,
  data = {},
  headers = {},
  useCache = false,
  params = {},
  auth = true,
  userService = true,
  locale = true,
  setTimeParam = true,
}) => {
  const ts = new Date().getTime();

  if (method.toUpperCase() === "POST") {
    data.RequestInfo = { apiId: "Rainmaker" };

    if (auth) {
      data.RequestInfo = { ...data.RequestInfo, ...requestInfo() };
    }
    if (userService) {
      data.RequestInfo = { ...data.RequestInfo, ...userServiceData() };
    }
    if (locale) {
      data.RequestInfo = { ...data.RequestInfo, msgId: `${ts}|${Digit.StoreData.getCurrentLanguage()}` };
    }
  }

  if (setTimeParam && !useCache) {
    params._ = Date.now();
  }

  const tenantId = Digit.ULBService.getCurrentTenantId() || Digit.ULBService.getStateId();
  if (!params["tenantId"] && window?.globalConfigs?.getConfig("ENABLE_SINGLEINSTANCE")) {
    params["tenantId"] = tenantId;
  }

  const res = await Axios({ method, url, data, params, headers });
  return res?.data || res?.response?.data || {};
};

export const CustomService = {
  getResponse: ({
    url,
    params,
    body,
    useCache = true,
    userService = true,
    setTimeParam = true,
    auth = true,
    headers = {},
    method = "POST",
  }) =>
    Request({
      url,
      data: body,
      useCache,
      userService,
      method,
      auth,
      params,
      headers,
      setTimeParam,
    }),
};
