import { execSync } from 'node:child_process'
import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { nodePolyfills } from 'vite-plugin-node-polyfills'
import vuetify from 'vite-plugin-vuetify';

function getVersion() {
  // Try to get the version via `git` if available; otherwise fall back on
  // the COMMIT_REF environment variable provided by Netlify's build
  // environment; if that is missing, report "unknown" as the version.

  try {
    return execSync('git describe --tags').toString();
  } catch (err) {
    return process.env.COMMIT_REF ? process.env.COMMIT_REF : 'unknown';
  }
}

function getGitRevision() {
  try {
    return execSync('git rev-parse HEAD').toString();
  } catch (err) {
    return '';
  }
}

process.env.VITE_APP_VERSION = getVersion();
process.env.VITE_APP_GIT_REVISION = getGitRevision();


// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vuetify(),
    // Some dependencies, such as`@apidevtools/json-schema-ref-parser`,
    // use Node APIs and require polyfills to work in the browser.
    nodePolyfills(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})
