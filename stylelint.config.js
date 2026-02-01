const config = {
  plugins: [
    "stylelint-gamut",
    "stylelint-use-logical",
    "stylelint-use-nesting",
    "stylelint-group-selectors",
    "stylelint-rem-over-px",
  ],
  extends: "stylelint-config-standard",
  rules: {
    "no-invalid-position-declaration": null,
    "media-feature-range-notation": "prefix",
    "plugin/stylelint-group-selectors": true,
    "property-no-vendor-prefix": null,
    "rem-over-px/rem-over-px": [
      true,
      {
        ignore: [
          "0.5px",
          "1px",
          "2px",
          "3px",
          "4px",
          "5px",
          "6.66px",
          "11.5px",
          "16px",
          "72px",
          "200px",
          "320px",
          "480px",
          "544px",
          "768px",
          "960px",
          "1024px",
          "1536px",
        ],
        ignoreAtRules: ["media"],
        fontSize: 16,
      },
    ],
    "selector-class-pattern": null,
    "selector-id-pattern": null,
    "value-no-vendor-prefix": null,
    "selector-no-vendor-prefix": [
      true,
      {
        ignoreSelectors: ["/-webkit-/"],
      },
    ],
  },
};
// noinspection JSUnusedGlobalSymbols
export default config;
