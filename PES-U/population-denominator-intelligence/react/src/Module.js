import { Loader } from "@egovernments/digit-ui-components";
import React from "react";
import { useRouteMatch } from "react-router-dom";
import { default as EmployeeApp } from "./pages/employee";
import { overrideHooks, updateCustomConfigs } from "./utils";
import PDICard from "./components/PDICard";
import hooks from "./hooks";

export const PDIModule = ({ stateCode, userType, tenants }) => {
  const { path } = useRouteMatch();
  const moduleCode = ["hcm-pdi"];
  const modulePrefix = "";
  const language = Digit.StoreData.getCurrentLanguage();
  const { isLoading, data: store } = Digit.Services.useStore({
    stateCode,
    moduleCode,
    language,
    modulePrefix,
  });

  if (isLoading) {
    return <Loader className={"digit-center-loader"} />;
  }

  return (
    <EmployeeApp path={path} stateCode={stateCode} userType={userType} tenants={tenants} />
  );
};

const componentsToRegister = {
  PDIModule,
  PDICard,
};

export const initPDIComponents = () => {
  overrideHooks();
  updateCustomConfigs();

  // Register hooks globally so other modules can use them
  // Access via: Digit.Hooks.pdi.usePopulationData(...)
  Object.assign(Digit.Hooks, { pdi: hooks });

  Object.entries(componentsToRegister).forEach(([key, value]) => {
    Digit.ComponentRegistryService.setComponent(key, value);
  });
};
