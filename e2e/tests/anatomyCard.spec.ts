import { expect, test, type Page } from "@playwright/test";
import { faker } from "@faker-js/faker";
import { clientUrl, registerNewUser, registerDandiset } from "../utils.ts";

const ADD_ANATOMY_BUTTON_TEXT = "Add anatomical information";
const EMPTY_STATE_TEXT = "No anatomical information provided.";

test.describe("anatomy card", () => {
  // Run serially so the owner's session (and the dandiset it creates) can be
  // reused across tests, instead of registering a fresh user + dandiset per test.
  // By default the DANDI test suite runs fully parallel, in which case `beforeAll`
  // would be run in each worker if tests in this file got split between workers.
  test.describe.configure({ mode: "serial" });

  let ownerPage: Page;
  let dandisetId: string | undefined;

  test.beforeAll(async ({ browser }) => {
    ownerPage = await browser.newPage();
    await registerNewUser(ownerPage);
    const dandisetName = faker.lorem.words();
    const dandisetDescription = faker.lorem.sentences();
    dandisetId = await registerDandiset(ownerPage, dandisetName, dandisetDescription);
  });

  test.afterAll(async () => {
    await ownerPage.close();
  });

  test("add-anatomy button is not visible to a non-owner", async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto(`${clientUrl}/#/dandiset/${dandisetId}/draft`);

    await expect(page.getByText(EMPTY_STATE_TEXT)).toBeVisible();
    await expect(
      page.getByRole("button", { name: ADD_ANATOMY_BUTTON_TEXT }),
    ).toHaveCount(0);

    await context.close();
  });

  test("owner can open the meditor to a pre-filled Anatomy item", async () => {
    await ownerPage.goto(`${clientUrl}/#/dandiset/${dandisetId}/draft`);

    await expect(ownerPage.getByText(EMPTY_STATE_TEXT)).toBeVisible();
    const addButton = ownerPage.getByRole("button", { name: ADD_ANATOMY_BUTTON_TEXT });
    await expect(addButton).toBeVisible();
    await addButton.click();

    await expect(ownerPage.getByRole("dialog")).toBeVisible();
    await expect(ownerPage.getByRole("button", { name: "Save Item" })).toBeVisible();
    await expect(ownerPage.getByRole("button", { name: "Add Item" })).toHaveCount(0);

    await expect(
      ownerPage.getByRole("combobox").filter({ hasText: "Anatomy" }),
    ).toBeVisible();
  });
});
