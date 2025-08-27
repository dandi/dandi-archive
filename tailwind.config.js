/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./dandiapi/api/templates/**/*.html",
    "./static/src/**/*.js",
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('daisyui'),
  ],
  daisyui: {
    themes: ["light", "dark"],
  },
}