# AGENTS.md

Guidance for coding agents working in this repository.

## Instructions

- When writing or changing Vuetify components in the Vue frontend (`web/src`) —
  adding navigation, click handling, or layout/spacing, or about to add a
  `<style scoped>` block, a wrapper `<a>`/`<router-link>`, or a JS click handler
  that navigates — follow `.claude/skills/vuetify-component-api/SKILL.md`:
  prefer Vuetify's own props and utility classes over custom CSS and imperative
  handlers.
