import React from "react";
import { useTranslation } from "react-i18next";

const PDICard = () => {
  const { t } = useTranslation();

  return (
    <div className="employeeCard card-home">
      <div className="complaint-links-container">
        <div className="header">
          <span className="logo">
            {/* TODO: Add PDI icon */}
          </span>
          <span className="text">{t("PDI_CARD_HEADER")}</span>
        </div>
        <div className="body">
          <span className="link">
            <a href={`/${window?.contextPath}/employee/pdi/dashboard`}>
              {t("PDI_VIEW_DASHBOARD")}
            </a>
          </span>
        </div>
      </div>
    </div>
  );
};

export default PDICard;
