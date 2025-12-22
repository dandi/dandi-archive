// Plugins
import Components from 'unplugin-vue-components/vite'
import Vue from '@vitejs/plugin-vue'
import { nodePolyfills } from 'vite-plugin-node-polyfills'
import Vuetify, { transformAssetUrls } from 'vite-plugin-vuetify'
import ViteFonts from 'unplugin-fonts/vite'
import VueRouter from 'unplugin-vue-router/vite'

// Utilities
import { defineConfig, loadEnv } from 'vite'
import { execSync } from 'node:child_process'
import { fileURLToPath, URL } from 'node:url'

import { commonjsDeps } from '@koumoul/vjsf/utils/build.js'

function getVersion() {
  // Try to get the version via `git` if available; otherwise fall back on
  // the COMMIT_REF environment variable provided by Netlify's build
  // environment; if that is missing, report "unknown" as the version.

  try {
    return execSync('git describe --tags').toString();
  } catch {
    return process.env.COMMIT_REF ? process.env.COMMIT_REF : 'unknown';
  }
}

function getGitRevision() {
  try {
    return execSync('git rev-parse HEAD').toString();
  } catch {
    return '';
  }
}

process.env.VITE_APP_VERSION = getVersion();
process.env.VITE_APP_GIT_REVISION = getGitRevision();


// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd());

  return {
    plugins: [
      VueRouter(),
      Vue({
        template: { transformAssetUrls },
      }),
      // https://github.com/vuetifyjs/vuetify-loader/tree/master/packages/vite-plugin#readme
      Vuetify({
        autoImport: true,
        styles: {
          configFile: 'src/styles/settings.scss',
        },
      }),
      Components(),
      ViteFonts({
        google: {
          families: [{
            name: 'Roboto',
            styles: 'wght@100;300;400;500;700;900',
          }],
        },
      }),
      nodePolyfills(),
    ],
    define: { 'process.env': {} },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
        // TODO: this is a fix for a bug in vite, see https://github.com/vitejs/vite/discussions/8549#discussioncomment-7333115
        '@jsdevtools/ono': '@jsdevtools/ono/cjs/index.js',
      },
      extensions: [
        '.js',
        '.json',
        '.jsx',
        '.mjs',
        '.ts',
        '.tsx',
        '.vue',
      ],
    },
    server: {
      host: process.env.VITE_HOST || 'localhost',
      port: 8085,
      proxy: {
        '/sitemap.xml': {
          target: `${env.VITE_APP_DANDI_BACKEND_ROOT}/sitemaps/frontend.xml`,
          changeOrigin: true,
          rewrite: () => '',
        }
      }
    },
    css: {
      preprocessorOptions: {
        sass: {
          api: 'modern-compiler',
        },
      },
    },
    // https://koumoul-dev.github.io/vuetify-jsonschema-form/latest/getting-started
    optimizeDeps: {
      include: commonjsDeps,
    },
    build: {
      commonjsOptions: {
        transformMixedEsModules: true,
      },
    },
  };
})
