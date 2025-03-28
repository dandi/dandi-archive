import { createPinia } from 'pinia';
import { createSentryPiniaPlugin } from '@sentry/vue';

const pinia = createPinia();
pinia.use(createSentryPiniaPlugin());

export default pinia;
