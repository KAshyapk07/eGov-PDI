import React from "react";
import { Switch, useRouteMatch } from "react-router-dom";
import { PrivateRoute } from "@egovernments/digit-ui-react-components";
import Dashboard from "./Dashboard";

const App = ({ path, stateCode, userType, tenants }) => {
  const { url } = useRouteMatch();

  return (
    <Switch>
      <PrivateRoute
        path={`${path}/dashboard`}
        component={() => <Dashboard stateCode={stateCode} />}
      />
    </Switch>
  );
};

export default App;
