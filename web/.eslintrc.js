module.exports = {
  root: true,
  env: {
    node: true,
  },
  plugins: [
    'vuetify',
  ],
  extends: [
    'eslint:recommended',
    'plugin:vue/recommended',
    '@vue/airbnb',
    '@vue/typescript',
  ],
  rules: {
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
  },
  parserOptions: {
    parser: '@typescript-eslint/parser',
  },
};
