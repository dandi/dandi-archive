/* eslint-env node */
require("@rushstack/eslint-patch/modern-module-resolution");

module.exports = {
  "root": true,
  "env": {
    "node": true,
  },
  "extends": [
    "plugin:vue/essential",
    "plugin:import/recommended",
    "plugin:import/typescript",
    "eslint:recommended",
    "@vue/eslint-config-typescript",
  ],
  settings: {
    "import/resolver": {
      typescript: {
        project: "."
      }
    },
  },
}
