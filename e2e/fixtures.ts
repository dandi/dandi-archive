import { test as base, type BrowserContext } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";

export { expect } from "@playwright/test";

// When the web app is built with VITE_COVERAGE=true, it is instrumented by
// Istanbul and accumulates coverage data in `window.__coverage__`. That data is
// lost whenever a page navigates away or is closed, so dump it to
// `<coverageDir>/*.json` (nyc's raw format) right before either happens.
// Nothing is written when the app is not instrumented.

declare global {
  interface Window {
    __coverage__?: object;
    __saveCoverage__?: (coverage: string) => Promise<void>;
  }
}

async function instrumentContext(context: BrowserContext, coverageDir: string) {
  const save = (coverage: string) =>
    writeFileSync(path.join(coverageDir, `${randomUUID()}.json`), coverage);

  await context.exposeFunction("__saveCoverage__", save);
  await context.addInitScript(() => {
    window.addEventListener("beforeunload", () => {
      if (window.__coverage__) {
        window.__saveCoverage__?.(JSON.stringify(window.__coverage__));
      }
    });
  });

  // Collect from all still-open pages before the context is closed; this
  // covers the default `context`/`page` fixtures as well as contexts and pages
  // created explicitly by tests (`browser.newPage()` closes its own context).
  const close = context.close.bind(context);
  context.close = async (...args) => {
    for (const page of context.pages()) {
      const coverage = await page
        .evaluate(() => (window.__coverage__ ? JSON.stringify(window.__coverage__) : null))
        .catch(() => null);
      if (coverage) {
        save(coverage);
      }
    }
    return close(...args);
  };
}

export const test = base.extend<object, { _coverage: void }>({
  _coverage: [
    async ({ browser }, use, workerInfo) => {
      const coverageDir = path.join(
        path.dirname(workerInfo.config.configFile ?? process.cwd()),
        ".nyc_output",
      );
      mkdirSync(coverageDir, { recursive: true });

      const newContext = browser.newContext.bind(browser);
      browser.newContext = async (...args) => {
        const context = await newContext(...args);
        await instrumentContext(context, coverageDir);
        return context;
      };
      await use();
      browser.newContext = newContext;
    },
    { scope: "worker", auto: true },
  ],
});
