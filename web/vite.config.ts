import { execSync } from 'node:child_process'
import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import legacy from '@vitejs/plugin-legacy'
import vue2 from '@vitejs/plugin-vue2'
import { nodePolyfills } from 'vite-plugin-node-polyfills'
import { VuetifyResolver } from 'unplugin-vue-components/resolvers';
import Components from 'unplugin-vue-components/vite';

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
  server: {
    port: 8085,
  },
  plugins: [
    vue2(),
    legacy({
      targets: ['ie >= 11'],
      additionalLegacyPolyfills: ['regenerator-runtime/runtime']
    }),
    nodePolyfills(),
    Components({
      resolvers: [
        // Vuetify
        VuetifyResolver(),
      ],
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})
