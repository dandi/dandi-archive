import { expect, test } from "@playwright/test";
import { clientUrl, registerNewUser, registerDandiset } from "../utils.ts";
import { faker } from "@faker-js/faker";

/**
 * Tests that listing query parameters (page, sortOption, sortDir, showDrafts,
 * showEmpty, search, pos) do not leak into Dandiset Landing Page (DLP) URLs,
 * and vice-versa.  See https://github.com/dandi/dandi-archive/issues/1460
 */

const LISTING_PARAMS = ["page", "sortOption", "sortDir", "showDrafts", "showEmpty", "search", "pos"];

/** Assert that none of the listing-specific params appear in the current URL. */
function expectCleanDlpUrl(url: string) {
  const parsed = new URL(url);
  for (const param of LISTING_PARAMS) {
    expect(parsed.searchParams.has(param), `URL should not contain '${param}': ${url}`).toBeFalsy();
  }
}

test.describe("URL parameter isolation (issue #1460)", () => {
  test("listing params do not leak to DLP when clicking a dandiset", async ({ page }) => {
    await registerNewUser(page);
    const name = faker.lorem.words();
    const description = faker.lorem.sentences();
    await registerDandiset(page, name, description);

    // Go to the public dandisets listing
    await page.goto(`${clientUrl}/dandiset`);
    await page.waitForLoadState("networkidle");

    // Click the first dandiset in the list
    await page.locator(".v-list-item").first().click();
    await page.waitForLoadState("networkidle");

    // DLP URL must be clean
    expectCleanDlpUrl(page.url());
    // Should be on a dandiset page
    expect(page.url()).toMatch(/\/dandiset\/\d+/);
  });

  test("search params do not leak to DLP", async ({ page }) => {
    await registerNewUser(page);
    const name = `searchtest-${faker.lorem.word()}`;
    const description = faker.lorem.sentences();
    await registerDandiset(page, name, description);

    // Navigate to search with a query
    await page.goto(`${clientUrl}/dandiset/search?search=${name}`);
    await page.waitForLoadState("networkidle");

    // Verify search results appear
    const items = page.locator(".v-list-item");
    await expect(items.first()).toBeVisible();

    // Click the first result
    await items.first().click();
    await page.waitForLoadState("networkidle");

    // DLP URL must be clean — no search param
    expectCleanDlpUrl(page.url());
  });

  test("direct DLP navigation produces clean URL", async ({ page }) => {
    await registerNewUser(page);
    const name = faker.lorem.words();
    const description = faker.lorem.sentences();
    const dandisetId = await registerDandiset(page, name, description);

    // Navigate directly to the DLP
    await page.goto(`${clientUrl}/dandiset/${dandisetId}`);
    await page.waitForLoadState("networkidle");

    expectCleanDlpUrl(page.url());
  });

  test("DLP pagination does not add listing params to URL", async ({ page }) => {
    test.slow();
    await registerNewUser(page);

    // Create multiple dandisets so pagination has something to page through
    for (let i = 0; i < 3; i += 1) {
      await registerDandiset(page, faker.lorem.words(), faker.lorem.sentences());
    }

    // Go to listing and click a dandiset
    await page.goto(`${clientUrl}/dandiset`);
    await page.waitForLoadState("networkidle");
    await page.locator(".v-list-item").first().click();
    await page.waitForLoadState("networkidle");

    // If pagination is visible, click next and verify URL stays clean
    const nextButton = page.locator(".v-pagination__next button");
    if (await nextButton.isVisible()) {
      await nextButton.click();
      await page.waitForLoadState("networkidle");
      expectCleanDlpUrl(page.url());
    }
  });

  test("back button from DLP restores listing params", async ({ page }) => {
    await registerNewUser(page);
    await registerDandiset(page, faker.lorem.words(), faker.lorem.sentences());

    // Go to listing
    await page.goto(`${clientUrl}/dandiset`);
    await page.waitForLoadState("networkidle");

    // Capture listing URL
    const listingUrl = page.url();

    // Click into a dandiset
    await page.locator(".v-list-item").first().click();
    await page.waitForLoadState("networkidle");

    // Go back
    await page.goBack();
    await page.waitForLoadState("networkidle");

    // Should be back on listing with its own params intact
    const backUrl = new URL(page.url());
    expect(backUrl.pathname).toBe("/dandiset");
  });

  test("manually appended listing params are stripped from DLP URL", async ({ page }) => {
    await registerNewUser(page);
    const name = faker.lorem.words();
    const description = faker.lorem.sentences();
    const dandisetId = await registerDandiset(page, name, description);

    // Navigate to DLP with manually injected listing params
    await page.goto(
      `${clientUrl}/dandiset/${dandisetId}?page=2&sortOption=1&sortDir=-1&showDrafts=true&showEmpty=false&search=test&pos=5`
    );
    await page.waitForLoadState("networkidle");

    // The router guard should have stripped all listing params
    expectCleanDlpUrl(page.url());
  });
});

test.describe("DLP tab URL state", () => {
  test("clicking 'How to Cite' tab adds ?tab=how-to-cite to URL", async ({ page }) => {
    await registerNewUser(page);
    const dandisetId = await registerDandiset(page, faker.lorem.words(), faker.lorem.sentences());

    await page.goto(`${clientUrl}/dandiset/${dandisetId}`);
    await page.waitForLoadState("networkidle");

    // URL should have no tab param on Overview (default)
    expect(new URL(page.url()).searchParams.has("tab")).toBeFalsy();

    // Click "How to Cite" tab
    await page.getByRole("tab", { name: "How to Cite" }).click();
    await page.waitForTimeout(500);

    // URL should now have ?tab=how-to-cite
    const url = new URL(page.url());
    expect(url.searchParams.get("tab")).toBe("how-to-cite");
  });

  test("switching back to Overview removes tab param", async ({ page }) => {
    await registerNewUser(page);
    const dandisetId = await registerDandiset(page, faker.lorem.words(), faker.lorem.sentences());

    await page.goto(`${clientUrl}/dandiset/${dandisetId}?tab=how-to-cite`);
    await page.waitForLoadState("networkidle");

    // Should be on How to Cite tab
    await expect(page.getByText("How to Cite this Dataset")).toBeVisible();

    // Switch to Overview
    await page.getByRole("tab", { name: "Overview" }).click();
    await page.waitForTimeout(500);

    // tab param should be gone
    expect(new URL(page.url()).searchParams.has("tab")).toBeFalsy();
  });

  test("navigating to ?tab=how-to-cite opens the correct tab", async ({ page }) => {
    await registerNewUser(page);
    const dandisetId = await registerDandiset(page, faker.lorem.words(), faker.lorem.sentences());

    // Navigate directly with tab param
    await page.goto(`${clientUrl}/dandiset/${dandisetId}?tab=how-to-cite`);
    await page.waitForLoadState("networkidle");

    // The How to Cite content should be visible
    await expect(page.getByText("How to Cite this Dataset")).toBeVisible();
  });

  test("tab param survives page reload", async ({ page }) => {
    await registerNewUser(page);
    const dandisetId = await registerDandiset(page, faker.lorem.words(), faker.lorem.sentences());

    await page.goto(`${clientUrl}/dandiset/${dandisetId}`);
    await page.waitForLoadState("networkidle");

    // Click How to Cite
    await page.getByRole("tab", { name: "How to Cite" }).click();
    await page.waitForTimeout(500);

    // Reload
    await page.reload();
    await page.waitForLoadState("networkidle");

    // Should still be on How to Cite
    await expect(page.getByText("How to Cite this Dataset")).toBeVisible();
    expect(new URL(page.url()).searchParams.get("tab")).toBe("how-to-cite");
  });
});

test.describe("DLP citation format URL state", () => {
  test("selecting a citation format adds ?format= to URL", async ({ page }) => {
    await registerNewUser(page);
    const dandisetId = await registerDandiset(page, faker.lorem.words(), faker.lorem.sentences());

    await page.goto(`${clientUrl}/dandiset/${dandisetId}?tab=how-to-cite`);
    await page.waitForLoadState("networkidle");

    // Default (APA) should have no format param
    expect(new URL(page.url()).searchParams.has("format")).toBeFalsy();

    // Select BibTeX format
    await page.locator(".citation-format-select").click();
    await page.getByRole("option", { name: "BibTeX" }).click();
    await page.waitForTimeout(500);

    const url = new URL(page.url());
    expect(url.searchParams.get("format")).toBe("bibtex");
    expect(url.searchParams.get("tab")).toBe("how-to-cite");
  });

  test("navigating to ?tab=how-to-cite&format=harvard opens correct format", async ({ page }) => {
    await registerNewUser(page);
    const dandisetId = await registerDandiset(page, faker.lorem.words(), faker.lorem.sentences());

    await page.goto(`${clientUrl}/dandiset/${dandisetId}?tab=how-to-cite&format=harvard`);
    await page.waitForLoadState("networkidle");

    // Harvard should be selected in the dropdown
    await expect(page.locator(".citation-format-select")).toContainText("Harvard");
  });

  test("switching back to APA removes format param", async ({ page }) => {
    await registerNewUser(page);
    const dandisetId = await registerDandiset(page, faker.lorem.words(), faker.lorem.sentences());

    await page.goto(`${clientUrl}/dandiset/${dandisetId}?tab=how-to-cite&format=bibtex`);
    await page.waitForLoadState("networkidle");

    // Select APA (default)
    await page.locator(".citation-format-select").click();
    await page.getByRole("option", { name: "APA 7th" }).click();
    await page.waitForTimeout(500);

    // format param should be gone, tab should remain
    const url = new URL(page.url());
    expect(url.searchParams.has("format")).toBeFalsy();
    expect(url.searchParams.get("tab")).toBe("how-to-cite");
  });
});

test.describe("DLP meditor overlay URL state", () => {
  test("opening meditor adds ?overlay=meditor to URL", async ({ page }) => {
    await registerNewUser(page);
    await registerDandiset(page, faker.lorem.words(), faker.lorem.sentences());
    await page.waitForLoadState("networkidle");

    // No overlay param initially
    expect(new URL(page.url()).searchParams.has("overlay")).toBeFalsy();

    // Click the metadata edit button to open meditor
    await page.getByRole("button", { name: "Metadata" }).click();
    await page.waitForTimeout(500);

    expect(new URL(page.url()).searchParams.get("overlay")).toBe("meditor");
  });

  test("closing meditor removes overlay param", async ({ page }) => {
    await registerNewUser(page);
    const dandisetId = await registerDandiset(page, faker.lorem.words(), faker.lorem.sentences());

    await page.goto(`${clientUrl}/dandiset/${dandisetId}?overlay=meditor`);
    await page.waitForLoadState("networkidle");

    // Meditor dialog should be open
    await expect(page.locator(".v-dialog--active, .v-overlay--active")).toBeVisible();

    // Close the dialog (press Escape)
    await page.keyboard.press("Escape");
    await page.waitForTimeout(500);

    // overlay param should be gone
    expect(new URL(page.url()).searchParams.has("overlay")).toBeFalsy();
  });

  test("navigating to ?overlay=meditor opens the meditor", async ({ page }) => {
    await registerNewUser(page);
    const dandisetId = await registerDandiset(page, faker.lorem.words(), faker.lorem.sentences());

    await page.goto(`${clientUrl}/dandiset/${dandisetId}?overlay=meditor`);
    await page.waitForLoadState("networkidle");

    // Meditor dialog should be visible
    await expect(page.locator(".v-dialog--active, .v-overlay--active")).toBeVisible();
  });
});
