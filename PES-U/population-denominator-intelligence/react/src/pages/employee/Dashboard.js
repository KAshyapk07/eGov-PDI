import React from "react";
import { useTranslation } from "react-i18next";
import { Header } from "@egovernments/digit-ui-react-components";

const Dashboard = ({ stateCode }) => {
  const { t } = useTranslation();

  return (
    <div>
      <Header>{t("PDI_DASHBOARD_HEADER")}</Header>
      {/* Population Denominator Intelligence Dashboard */}
      {/* TODO: Add settlement-level population estimation map */}
      {/* TODO: Add coverage gap indicators */}
      {/* TODO: Add WorldPop vs registration comparison charts */}
    </div>
  );
};

export default Dashboard;
