import { type Page } from "@playwright/test";
import { faker } from "@faker-js/faker";

const TEST_USER_INITIALS = "AA";
const LOGOUT_BUTTON_TEXT = "Logout";
const LOGIN_BUTTON_TEXT = "Log In with GitHub";
const clientUrl = "http://localhost:8085";

function uniqueId() {
  return Date.now().toString();
}

async function registerNewUser(page: Page) {
  const email = faker.internet.email();
  const password = "Xtra-S3curi7y-p4sSw0rd";

  const firstname = faker.person.firstName();
  const lastname = faker.person.lastName();

  await page.goto(clientUrl);
  await page.getByRole("button", { name: LOGIN_BUTTON_TEXT }).click();
  await page.goto(page.url().replace("/accounts/login", "/accounts/signup"));
  await page.getByPlaceholder("Email address").click();
  await page.getByPlaceholder("Email address").fill(email);
  await page.getByPlaceholder("Password").first().click();
  await page.getByPlaceholder("Password").first().fill(password);
  await page.getByPlaceholder("Password (again)").click();
  await page.getByPlaceholder("Password (again)").fill(password);
  await page.getByRole("button", { name: "Sign Up " }).click();
  await page.getByLabel("First Name").click({ force: true });
  await page.getByLabel("First Name").fill(firstname);
  await page.getByLabel("Last Name").click({ force: true });
  await page.getByLabel("Last Name").fill(lastname);
  await page.keyboard.press(" ");  // Using locator.fill does not enable to button for some reason
  await page.waitForTimeout(1000);
  await page.keyboard.press("Backspace");
  await page.waitForTimeout(1000);
  await page.getByRole("button").click();

  return { email, firstname, lastname, password };
}

async function dismissCookieBanner(page: Page) {
  const cookieBannerDismissButtonCount = await page.getByText("Got it!").count();
  if (cookieBannerDismissButtonCount) {
    await page.getByText("Got it!").click();
  }
}

async function registerDandiset(page: Page, name: string, description: string) {
  await dismissCookieBanner(page);
  await page.getByRole("link", { name: "New Dandiset" }).click();
  await page.getByLabel("Title").click();
  await page.getByLabel("Title").fill(name);
  await page.getByLabel("Description").click();
  await page.getByLabel("Description").fill(description);
  await page.getByLabel("License").click()
  await page.getByRole("option", { name: "spdx:CC0-" }).click();
  await page.getByRole("button", { name: "Register Dandiset" }).click();
  await page.waitForTimeout(250);
  const dandisetId = await page.url().split("/").pop();
  return dandisetId;
}

async function gotoAndLogin(page: Page) {
  await page.goto(clientUrl);
  await page.getByRole("button", { name: LOGIN_BUTTON_TEXT }).click();
  await page.getByPlaceholder("Email address").click();
  await page.getByPlaceholder("Email address").fill("admin@kitware.com");
  await page.getByPlaceholder("Password").click();
  await page.getByPlaceholder("Password").fill("password");
  await page.getByRole("button", { name: "Sign In " }).click();
}

export {
  clientUrl,
  TEST_USER_INITIALS,
  LOGOUT_BUTTON_TEXT,
  LOGIN_BUTTON_TEXT,
  dismissCookieBanner,
  gotoAndLogin,
  registerDandiset,
  registerNewUser,
  uniqueId,
};
