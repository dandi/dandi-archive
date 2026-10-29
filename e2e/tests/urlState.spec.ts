import { expect, test, type Page } from "@playwright/test";
import { clientUrl } from "../utils.ts";

// UI state that is kept in the URL, so that reloading or sharing the URL brings back the
// same view.
const dandisetUrl = `${clientUrl}/dandiset/000003/draft`;

function queryOf(page: Page) {
  return Object.fromEntries(new URL(page.url()).searchParams);
}

test.describe("Dandiset landing page tab", () => {
  test("selecting a tab is reflected in the URL", async ({ page }) => {
    await page.goto(dandisetUrl);

    await page.getByRole("tab", { name: "How to Cite" }).click();
    await expect.poll(() => queryOf(page)).toEqual({ tab: "how-to-cite" });

    await page.getByRole("tab", { name: "Overview" }).click();
    await expect.poll(() => queryOf(page)).toEqual({});
  });

  test("the tab in the URL is selected, also after a reload", async ({ page }) => {
    await page.goto(`${dandisetUrl}?tab=how-to-cite`);
    await expect(page.getByText("How to Cite this Dataset")).toBeVisible();

    await page.reload();
    await expect(page.getByText("How to Cite this Dataset")).toBeVisible();
    expect(queryOf(page)).toEqual({ tab: "how-to-cite" });
  });

  test("an unknown tab in the URL shows the Overview tab", async ({ page }) => {
    await page.goto(`${dandisetUrl}?tab=nonsense`);
    await expect(page.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
  });
});

test.describe("Citation format", () => {
  test("selecting a format is reflected in the URL and survives a reload", async ({ page }) => {
    await page.goto(`${dandisetUrl}?tab=how-to-cite`);

    await page.locator(".citation-format-select").click();
    await page.getByRole("option", { name: "BibTeX" }).click();
    await expect.poll(() => queryOf(page)).toEqual({ tab: "how-to-cite", format: "bibtex" });

    await page.reload();
    await expect(page.locator(".citation-format-select")).toContainText("BibTeX");

    // Back to the default format drops the parameter.
    await page.locator(".citation-format-select").click();
    await page.getByRole("option", { name: "APA 7th" }).click();
    await expect.poll(() => queryOf(page)).toEqual({ tab: "how-to-cite" });
  });

  test("leaving the How to Cite tab drops the format", async ({ page }) => {
    await page.goto(`${dandisetUrl}?tab=how-to-cite&format=harvard`);
    await expect(page.locator(".citation-format-select")).toContainText("Harvard");

    await page.getByRole("tab", { name: "Overview" }).click();
    await expect.poll(() => queryOf(page)).toEqual({});
  });
});

test.describe("Meditor", () => {
  test("opening and closing the meditor is reflected in the URL", async ({ page }) => {
    await page.goto(dandisetUrl);

    await page.getByText("Metadata", { exact: true }).click();
    await expect(page.getByRole("tab", { name: "Dandiset contributors" })).toBeVisible();
    await expect.poll(() => queryOf(page)).toEqual({ overlay: "meditor" });

    await page.getByRole("tab", { name: "Dandiset contributors" }).click();
    await expect.poll(() => queryOf(page)).toEqual({ overlay: "meditor", meditorTab: "contributor" });

    await page.keyboard.press("Escape");
    await expect(page.getByRole("tab", { name: "Dandiset contributors" })).toBeHidden();
    await expect.poll(() => queryOf(page)).toEqual({});
  });

  test("the meditor and its tab in the URL are opened, also after a reload", async ({ page }) => {
    await page.goto(`${dandisetUrl}?overlay=meditor&meditorTab=contributor`);
    const contributorsTab = page.getByRole("tab", { name: "Dandiset contributors" });
    await expect(contributorsTab).toHaveAttribute("aria-selected", "true");

    await page.reload();
    await expect(contributorsTab).toHaveAttribute("aria-selected", "true");
    expect(queryOf(page)).toEqual({ overlay: "meditor", meditorTab: "contributor" });
  });
});

test.describe("Dandisets listing", () => {
  test("the Drafts and Empty Dandisets switches are restored from the URL", async ({ page }) => {
    await page.goto(`${clientUrl}/dandiset?showDrafts=false&showEmpty=true`);
    await page.getByRole("button", { name: "󰒓" }).click();

    await expect(page.getByLabel("Drafts")).not.toBeChecked();
    await expect(page.getByLabel("Empty Dandisets")).toBeChecked();
  });
});
