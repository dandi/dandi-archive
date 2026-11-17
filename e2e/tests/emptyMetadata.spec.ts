import { expect, test } from "@playwright/test";
import { faker } from "@faker-js/faker";
import { registerDandiset, registerNewUser } from "../utils.ts";

const apiUrl = "http://localhost:8000/api";

test.describe("empty metadata items", () => {
  test("draft dandiset shows fallback labels for nameless metadata items", async ({ page }) => {
    await registerNewUser(page);
    const dandisetName = faker.lorem.words();
    const dandisetDescription = faker.lorem.sentences();
    const dandisetId = await registerDandiset(page, dandisetName, dandisetDescription);

    const versionUrl = `${apiUrl}/dandisets/${dandisetId}/versions/draft/`;
    const getRes = await page.request.get(versionUrl);
    expect(getRes.ok()).toBeTruthy();
    const metadata = await getRes.json();

    // Nameless items are schema-valid (see https://github.com/dandi/dandi-schema/issues/442),
    // so the backend accepts these even though they have no identifying information.
    metadata.contributor = [
      ...(metadata.contributor ?? []),
      { schemaKey: "Organization", roleName: ["dcite:Funder"] },
    ];
    metadata.about = [
      ...(metadata.about ?? []),
      { schemaKey: "Anatomy" },
      { schemaKey: "Disorder" },
    ];

    // page.request shares the browser context's session cookie, so it's already
    // authenticated as this user. Session auth is DRF's first authenticator to
    // succeed here (it's tried before token auth and a valid session cookie is
    // present), so unsafe methods (PUT) also need the matching CSRF token echoed
    // back as a header.
    const cookies = await page.context().cookies();
    const csrfToken = cookies.find((c) => c.name === "csrftoken")?.value;

    const putRes = await page.request.put(versionUrl, {
      headers: { "X-CSRFToken": csrfToken ?? "" },
      data: { name: metadata.name, metadata },
    });
    expect(putRes.ok()).toBeTruthy();

    await page.reload();
    await page.getByRole("tab", { name: "Overview" }).click();

    // Funding information card: MetadataCard's per-item fallback label.
    await expect(page.getByText("Unnamed Item")).toBeVisible();
    // Anatomy card: its own dedicated fallback label.
    await expect(page.getByText("Unnamed region")).toBeVisible();
    // Subject matter chips: one per "about" entry, labeled by schemaKey.
    await expect(page.getByText("Unnamed Anatomy")).toBeVisible();
    await expect(page.getByText("Unnamed Disorder")).toBeVisible();
  });
});
