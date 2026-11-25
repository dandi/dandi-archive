import { expect, test } from "@playwright/test";
import { faker } from "@faker-js/faker";
import { clientUrl, registerDandiset, registerNewUser, uniqueId } from "../utils.ts";

// Opening a dandiset from a listing must not carry the listing's query params
// (page, sortOption, search, pos, ...) over into the dandiset's URL, and the
// dandiset page no longer pages through the listing it was opened from.
// See https://github.com/dandi/dandi-archive/issues/1460
test.describe("dandiset pages reached from a listing", () => {
  test("opening a search result gives a URL without params and no prev/next buttons", async ({ page }) => {
    await registerNewUser(page);
    const token = `urltest${uniqueId()}`;
    const name = `${token} ${faker.lorem.words()}`;
    const identifier = await registerDandiset(page, name, faker.lorem.sentences());

    await page.goto(`${clientUrl}/dandiset/search?search=${token}&sortOption=1&sortDir=1`);
    await page.getByText(name).click();

    await page.waitForURL(new RegExp(`/dandiset/${identifier}$`));
    expect(new URL(page.url()).search).toBe("");

    // The search field shares the toolbar the prev/next buttons used to be in.
    await expect(page.getByRole("textbox", { name: "Search Dandisets" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Previous page" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Next page" })).toHaveCount(0);
  });
});
