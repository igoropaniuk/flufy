// Injected at DocumentCreation to present this browser as Chrome.
// Template markers (e.g. {{CHROME_UA}}) are replaced by Python before injection.
(function () {
  "use strict";

  // --- Notification permission: auto-grant so the app skips its prompt banner ---
  Object.defineProperty(Notification, "permission", {
    get: function () {
      return "granted";
    },
  });
  Notification.requestPermission = function (cb) {
    if (cb) cb("granted");
    return Promise.resolve("granted");
  };

  // --- User-Agent spoofing ---
  const ua = "{{CHROME_UA}}";
  Object.defineProperty(navigator, "userAgent", {
    get: function () {
      return ua;
    },
  });
  Object.defineProperty(navigator, "appVersion", {
    get: function () {
      return ua;
    },
  });
  Object.defineProperty(navigator, "platform", {
    get: function () {
      return "{{PLATFORM_STRING}}";
    },
  });

  // --- Client Hints API (navigator.userAgentData) ---
  // Brand order and "Not" brand string match Chrome 140 stable.
  const brands = [
    { brand: "Chromium", version: "{{CHROME_VERSION}}" },
    { brand: "Google Chrome", version: "{{CHROME_VERSION}}" },
    { brand: "Not)A;Brand", version: "8" },
  ];
  const fullBrands = [
    { brand: "Chromium", version: "{{CHROME_FULL_VERSION}}" },
    { brand: "Google Chrome", version: "{{CHROME_FULL_VERSION}}" },
    { brand: "Not)A;Brand", version: "8.0.0.0" },
  ];

  const uaData = {
    brands: brands,
    mobile: false,
    platform: "Linux",
    getHighEntropyValues: function () {
      return Promise.resolve({
        brands: fullBrands,
        mobile: false,
        platform: "Linux",
        platformVersion: "7.0.0",
        architecture: "{{ARCH}}",
        bitness: "{{BITNESS}}",
        fullVersionList: fullBrands,
        model: "",
        uaFullVersion: "{{CHROME_FULL_VERSION}}",
      });
    },
    toJSON: function () {
      return {
        brands: this.brands,
        mobile: this.mobile,
        platform: this.platform,
      };
    },
  };

  Object.defineProperty(navigator, "userAgentData", {
    get: function () {
      return uaData;
    },
  });
})();
