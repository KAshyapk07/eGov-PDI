import UICustomizations from "../configs/UICustomizations";

export const overrideHooks = () => {
  // Override or extend default hooks if needed
};

export const updateCustomConfigs = () => {
  // Register module-specific UI customizations
  const defined = window?.Digit?.Customizations?.healthPdi || {};
  window.Digit = window.Digit || {};
  window.Digit.Customizations = {
    ...(window.Digit.Customizations || {}),
    healthPdi: {
      ...defined,
      ...UICustomizations,
    },
  };
};
