import { expect, test } from "@playwright/test";
import { registerDandiset, registerNewUser, uniqueId } from "../utils.ts";
import moment from "moment";
import { faker } from "@faker-js/faker";

test.describe("dandisets page", async () => {
    test("search for Dandisets", async ({ page }) => {
        test.slow();
        await registerNewUser(page);
        const dandisetIdentifierNameMapping: Map<string, string> = new Map();

        for (let i = 0; i < 10; i += 1) {
            const name = faker.lorem.words();
            const description = faker.lorem.sentences();
            const identifier = await registerDandiset(page, name, description);
            dandisetIdentifierNameMapping[identifier || ""] = name;
        }

        const searchFieldText = "Search Dandisets by name,";
        await page.getByRole('textbox', { name: 'Search Dandisets by name,' }).click();
        await page.keyboard.press("Enter");
        await page.getByRole("button", { name: "󰒓" }).click();
        await page.waitForTimeout(500);
        await page.getByText("Empty Dandisets").click();

        dandisetIdentifierNameMapping.forEach(async (name, id) => {
            await page.getByLabel(searchFieldText).click();
            await page.getByLabel(searchFieldText).fill(name);
            await page.keyboard.press("Enter");

            await expect(page.getByText(`DANDI:${id}`)).toHaveCount(1);

            // Clear search bar
            await page.keyboard.down("ControlLeft");
            await page.keyboard.press("A");
            await page.keyboard.press("Backspace");
            await page.keyboard.up("ControlLeft");
            await page.keyboard.press("Tab");
        });


    });
    test("view My Dandisets", async ({ page }) => {
        const { firstname, lastname } = await registerNewUser(page);
        const id = uniqueId();
        const name = `name ${id}`;
        const description = `description ${id}`;
        const identifier = await registerDandiset(page, name, description);
        await page.getByRole("link", { name: "My Dandisets" }).click();
        await expect(page.getByText(name)).toHaveCount(1);
        await expect(page.getByText(`DANDI:${identifier}`)).toHaveCount(1);
        await expect(page.getByText(`Contact ${lastname}, ${firstname}`)).toHaveCount(1);
        await expect(page.getByText(`Updated on ${moment(new Date()).format("LL")}`)).toHaveCount(1);
    });
});
