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
    // Every operator from the help table should be offered.
    await expect(listbox.getByRole("option")).toHaveCount(12);
    await expect(listbox.getByText("species:", { exact: true })).toBeVisible();
    await expect(listbox.getByText("created_after:", { exact: true })).toBeVisible();
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

  test("matches the start of an operator's words, not any substring", async ({ page }) => {
    await page.goto(clientUrl);
    await dismissCookieBanner(page);

    const search = page.getByPlaceholder(SEARCH_PLACEHOLDER);
    const listbox = page.locator(".operator-suggestions");
    await search.click();

    // "after" starts a word of created_after, modified_after and published_after.
    await search.fill("after");
    await expect(listbox.getByRole("option")).toHaveCount(3);

    // "ate" is inside "created", but doesn't start any operator word.
    await search.fill("ate");
    await expect(listbox).toBeHidden();
  });

  test("searches for a typed word on Enter, even if it names an operator", async ({ page }) => {
    await page.goto(clientUrl);
    await dismissCookieBanner(page);

    const search = page.getByPlaceholder(SEARCH_PLACEHOLDER);
    await search.click();
    await search.fill("species");
    // The dropdown still offers species:, but nothing is highlighted until the
    // user arrows into the list, so Enter searches for the word itself.
    await expect(page.locator(".operator-suggestions").getByRole("option")).toHaveCount(1);
    await page.keyboard.press("Enter");

    await expect(page).toHaveURL(/search=species(&|$)/);
    await expect(search).toHaveValue("species");
  });

  test("inserts the operator chosen with the arrow keys on Enter", async ({ page }) => {
    await page.goto(clientUrl);
    await dismissCookieBanner(page);

    const search = page.getByPlaceholder(SEARCH_PLACEHOLDER);
    await search.click();
    await search.fill("spe");
    await page.keyboard.press("ArrowDown");
    await expect(page.locator(".operator-suggestions").getByRole("option", { selected: true })).toHaveCount(1);
    await page.keyboard.press("Enter");

    await expect(search).toHaveValue("species:");
    // Focus stays in the field so the value can be typed straight away.
    await expect(search).toBeFocused();
  });

  test("completes an operator mid-query on Tab", async ({ page }) => {
    await page.goto(clientUrl);
    await dismissCookieBanner(page);

    const search = page.getByPlaceholder(SEARCH_PLACEHOLDER);
    await search.click();
    await search.fill("neuropixels appr");
    // Tab completes the top match for the word under the cursor.
    await page.keyboard.press("Tab");

    await expect(search).toHaveValue("neuropixels approach:");
  });

  test("inserts an operator on click", async ({ page }) => {
    await page.goto(clientUrl);
    await dismissCookieBanner(page);

    const search = page.getByPlaceholder(SEARCH_PLACEHOLDER);
    await search.click();
    await search.fill("stan");

    const listbox = page.locator(".operator-suggestions");
    await listbox.getByText("standard:", { exact: true }).click();

    await expect(search).toHaveValue("standard:");
  });

  test("dismisses the dropdown on Escape and submits on Enter when browsing", async ({ page }) => {
    await page.goto(clientUrl);
    await dismissCookieBanner(page);

    const search = page.getByPlaceholder(SEARCH_PLACEHOLDER);
    await search.click();

    const listbox = page.locator(".operator-suggestions");
    await expect(listbox).toBeVisible();
    // A heading marks the list as options to narrow the search, not history.
    await expect(listbox.getByText("Narrow your search")).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(listbox).toBeHidden();

    // With nothing highlighted (browsing the full list), Enter submits the
    // search and navigates to the search results route.
    await search.fill("hippocampus");
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/search=hippocampus/);
  });

  test.describe("values of categorical operators", () => {
    const SPECIES = [
      { value: "Mus musculus - House mouse", dandisets: 3 },
      { value: "Rattus norvegicus - Norway rat", dandisets: 1 },
    ];

    test.beforeEach(async ({ page }) => {
      // Serve the value list here: the fixture dandisets have no assets summary.
      await page.route(/\/api\/search\/operator-values\//, (route) => {
        const operator = new URL(route.request().url()).searchParams.get("operator");
        return route.fulfill({ json: operator === "species" ? SPECIES : [] });
      });
    });

    test("lists an operator's values after its colon, filtered as you type", async ({ page }) => {
      await page.goto(clientUrl);
      await dismissCookieBanner(page);

      const search = page.getByPlaceholder(SEARCH_PLACEHOLDER);
      const listbox = page.locator(".operator-suggestions");
      await search.click();
      await search.fill("species:");

      await expect(listbox.getByText("Species", { exact: true })).toBeVisible();
      await expect(listbox.getByRole("option")).toHaveCount(2);
      await expect(listbox.getByRole("option").first()).toContainText("Mus musculus - House mouse");
      await expect(listbox.getByRole("option").first()).toContainText("3");

      await search.fill("species:rat");
      await expect(listbox.getByRole("option")).toHaveCount(1);
      await expect(listbox.getByRole("option")).toContainText("Norway rat");
    });

    test("inserts a chosen value, quoted, and searches for it", async ({ page }) => {
      await page.goto(clientUrl);
      await dismissCookieBanner(page);

      const search = page.getByPlaceholder(SEARCH_PLACEHOLDER);
      await search.click();
      await search.fill("neuropixels species:rat");
      // Wait for the value list to arrive before moving into it.
      await expect(page.locator(".operator-suggestions").getByRole("option")).toHaveCount(1);
      await page.keyboard.press("ArrowDown");
      await page.keyboard.press("Enter");
      await expect(search).toHaveValue('neuropixels species:"Rattus norvegicus - Norway rat" ');

      // The menu now offers operators for the next term; close it and search.
      await page.keyboard.press("Escape");
      await page.keyboard.press("Enter");
      // The router may leave ":" and '"' unencoded in the query string.
      await expect(page).toHaveURL(/search=neuropixels(\+|%20)species(:|%3A)("|%22)Rattus(\+|%20)norvegicus/);
      // The trailing space after the chosen value isn't searched.
      await expect(page).not.toHaveURL(/rat("|%22)(\+|%20)(&|$)/);
    });

    test("searches for a typed value on Enter without choosing one", async ({ page }) => {
      await page.goto(clientUrl);
      await dismissCookieBanner(page);

      const search = page.getByPlaceholder(SEARCH_PLACEHOLDER);
      await search.click();
      await search.fill("species:mouse");
      await expect(page.locator(".operator-suggestions").getByRole("option")).toHaveCount(1);
      await page.keyboard.press("Enter");

      await expect(page).toHaveURL(/search=species(:|%3A)mouse(&|$)/);
    });
  });
});
