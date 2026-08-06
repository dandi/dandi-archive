import { test, expect } from "@playwright/test";
import { clientUrl, dismissCookieBanner } from "../utils.ts";

// The operator autocomplete dropdown is a pure-frontend feature: the operator
// list is hardcoded in the component, so these tests don't need any backend
// data. They exercise the search field on the home page (`/`).

const SEARCH_PLACEHOLDER = /Search Dandisets/;

test.describe("search operator autocomplete", async () => {
  test("shows the full operator list on focus", async ({ page }) => {
    await page.goto(clientUrl);
    await dismissCookieBanner(page);

    const search = page.getByPlaceholder(SEARCH_PLACEHOLDER);
    await search.click();

    const listbox = page.locator(".operator-suggestions");
    await expect(listbox).toBeVisible();

    // A few representative operators should be offered.
    await expect(listbox.getByText("species:", { exact: true })).toBeVisible();
    await expect(listbox.getByText("created_after:", { exact: true })).toBeVisible();

    const suggestionCount = await listbox.getByRole("option").count();
    expect(suggestionCount).toBeGreaterThan(0);

    // Every operator documented in the help table should be offered as a
    // suggestion. Both lists come from the same source in the component, so
    // compare counts rather than hardcoding a number that rots whenever an
    // operator is added or removed.
    await page.getByLabel("Show advanced search syntax help").click();
    const helpTable = page.locator(".advanced-search-help");
    await expect(helpTable).toBeVisible();
    await expect(helpTable.locator("tbody tr")).toHaveCount(suggestionCount);
  });

  test("filters operators as you type", async ({ page }) => {
    await page.goto(clientUrl);
    await dismissCookieBanner(page);

    const search = page.getByPlaceholder(SEARCH_PLACEHOLDER);
    await search.click();
    await search.fill("spe");

    const listbox = page.locator(".operator-suggestions");
    await expect(listbox.getByRole("option")).toHaveCount(1);
    await expect(listbox.getByText("species:", { exact: true })).toBeVisible();
    await expect(listbox.getByText("approach:", { exact: true })).toHaveCount(0);
  });

  test("inserts the highlighted operator on Enter", async ({ page }) => {
    await page.goto(clientUrl);
    await dismissCookieBanner(page);

    const search = page.getByPlaceholder(SEARCH_PLACEHOLDER);
    await search.click();
    await search.fill("spe");
    // The first match auto-highlights while typing a prefix, so Enter inserts
    // it (rather than submitting the search).
    await page.keyboard.press("Enter");

    await expect(search).toHaveValue("species:");
    // Focus stays in the field so the value can be typed straight away.
    await expect(search).toBeFocused();
  });

  test("inserts an operator mid-query on the token under the cursor", async ({ page }) => {
    await page.goto(clientUrl);
    await dismissCookieBanner(page);

    const search = page.getByPlaceholder(SEARCH_PLACEHOLDER);
    await search.click();
    await search.fill("neuropixels appr");
    await page.keyboard.press("Enter");

    await expect(search).toHaveValue("neuropixels approach:");
  });

  test("inserts an operator on click", async ({ page }) => {
    await page.goto(clientUrl);
    await dismissCookieBanner(page);

    const search = page.getByPlaceholder(SEARCH_PLACEHOLDER);
    await search.click();
    await search.fill("file");

    const listbox = page.locator(".operator-suggestions");
    await listbox.getByText("file_type:", { exact: true }).click();

    await expect(search).toHaveValue("file_type:");
  });

  test("dismisses the dropdown on Escape and submits on Enter when browsing", async ({ page }) => {
    await page.goto(clientUrl);
    await dismissCookieBanner(page);

    const search = page.getByPlaceholder(SEARCH_PLACEHOLDER);
    await search.click();

    const listbox = page.locator(".operator-suggestions");
    await expect(listbox).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(listbox).toBeHidden();

    // With nothing highlighted (browsing the full list), Enter submits the
    // search and navigates to the search results route.
    await search.fill("hippocampus");
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/search=hippocampus/);
  });
});
