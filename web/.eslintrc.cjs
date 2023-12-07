/* eslint-env node */
require('@rushstack/eslint-patch/modern-module-resolution');

module.exports = {
  root: true,
  env: {
    node: true,
  },
  extends: [
    'plugin:vue/essential',
    'plugin:vuetify/recommended',
    'plugin:import/recommended',
    'plugin:import/typescript',
    'eslint:recommended',
    '@vue/eslint-config-typescript',
  ],
  rules: {
    camelcase: 'off',
    'vuetify/no-deprecated-classes': 'error',
    'vuetify/grid-unknown-attributes': 'error',
    'vuetify/no-legacy-grid': 'error',
    'no-underscore-dangle': [
      'error',
      {
        allow: [
          '_id',
          '_modelType',
          '_accessLevel',
        ],
      },
    ],
    'lines-between-class-members': [
      'error',
      'always',
      {
        exceptAfterSingleLine: true,
      },
    ],
    'import/prefer-default-export': 'off',
    '@typescript-eslint/consistent-type-imports': 'error',
  },
  settings: {
    'import/resolver': {
      typescript: {
        project: '.'
      }
    },
  },
}
