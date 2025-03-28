/**
 * plugins/index.ts
 *
 * Automatically included in `./src/main.ts`
 */

import * as Sentry from '@sentry/vue';

// Plugins
import vuetify from './vuetify'
import pinia from './pinia'
import router from '../router'

// Types
import type { App } from 'vue'

export function registerPlugins (app: App) {
  app
    .use(vuetify)
    .use(router)
    .use(pinia)

  Sentry.init({
    app,
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.VITE_APP_SENTRY_ENVIRONMENT,
    integrations: [
      Sentry.browserTracingIntegration({ router }),
      Sentry.replayIntegration(),
      Sentry.vueIntegration({
        tracingOptions: {
          trackComponents: true,
        },
      }),
      Sentry.captureConsoleIntegration({
        levels: ['error', 'warn'],
      }),
    ],
    tracePropagationTargets: [import.meta.env.VITE_APP_DANDI_API_ROOT || ''],

    // Capture 1% of traces for Sentry performance
    tracesSampleRate: 0.01,
    // Capture info about Vue component props
    attachProps: true,

    // Capture Replay for 10% of all sessions,
    // plus for 100% of sessions with an error
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
  });
}
