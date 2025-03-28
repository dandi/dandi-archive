import { test, expect } from "@playwright/test";
import {
  LOGIN_BUTTON_TEXT,
  LOGOUT_BUTTON_TEXT,
  TEST_USER_INITIALS,
  gotoAndLogin,
} from "../utils.ts";

test.describe("account management", async () => {
  test("log a user out", async ({ page }) => {
    await gotoAndLogin(page);
    await page.getByRole("button", { name: TEST_USER_INITIALS }).click();
    await page.getByRole("menuitem", { name: LOGOUT_BUTTON_TEXT }).click();
    await expect(
      page.getByRole("button", { name: LOGIN_BUTTON_TEXT }),
    ).toHaveCount(1);
  });
  test("log a user in", async ({ page }) => {
    await gotoAndLogin(page);
    await expect(
      page.getByRole("button", { name: TEST_USER_INITIALS }),
    ).toHaveCount(1);
  });
});
