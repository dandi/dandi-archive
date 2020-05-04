// This filename is not magic; it is referenced by Jest's setupFilesAfterEnv

import { setDefaultOptions } from 'expect-puppeteer';

// Set the default action timeout to something greater than 500ms
setDefaultOptions({ timeout: 10000 });
