import { expect, test } from "@playwright/test";
import { faker } from "@faker-js/faker";
import { clientUrl, registerDandiset, registerNewUser, uniqueId } from "../utils.ts";

// Opening a dandiset from a listing must not carry the listing's query params
// (page, sortOption, search, pos, ...) over into the dandiset's URL.
// See https://github.com/dandi/dandi-archive/issues/1460
test.describe("dandiset URLs reached from a listing", () => {
  test("opening a search result leaves the dandiset URL without params", async ({ page }) => {
    await registerNewUser(page);
    const token = `urltest${uniqueId()}`;
    const name = `${token} ${faker.lorem.words()}`;
    const identifier = await registerDandiset(page, name, faker.lorem.sentences());

    await page.goto(`${clientUrl}/dandiset/search?search=${token}&sortOption=1&sortDir=1`);
    await page.getByText(name).click();

    await page.waitForURL(new RegExp(`/dandiset/${identifier}$`));
    expect(new URL(page.url()).search).toBe("");
  });

  test("prev/next on the dandiset page pages through the listing without adding params", async ({ page }) => {
    test.slow();
    await registerNewUser(page);
    const token = `urltest${uniqueId()}`;
    const identifiers = [
      await registerDandiset(page, `${token} ${faker.lorem.words()}`, faker.lorem.sentences()),
      await registerDandiset(page, `${token} ${faker.lorem.words()}`, faker.lorem.sentences()),
    ];

    await page.goto(`${clientUrl}/dandiset/search?search=${token}`);
    await expect(page.locator(".v-list-item")).toHaveCount(2);
    await page.locator(".v-list-item").first().click();
    await page.waitForURL(/\/dandiset\/\d+$/);
    const first = new URL(page.url()).pathname.split("/").pop();
    expect(identifiers).toContain(first);
    const second = identifiers.find((id) => id !== first);

    await page.getByRole("button", { name: "Next page" }).click();
    await page.waitForURL(new RegExp(`/dandiset/${second}$`));
    expect(new URL(page.url()).search).toBe("");

    // The position in the listing survives a reload even though it is not in the URL.
    await page.reload();
    await page.getByRole("button", { name: "Previous page" }).click();
    await page.waitForURL(new RegExp(`/dandiset/${first}$`));
    expect(new URL(page.url()).search).toBe("");
  });
});
