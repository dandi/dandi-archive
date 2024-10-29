import { test, expect, type Page } from "@playwright/test";

const clientUrl = "http://localhost:8085";

const noLicenseSelector = async (page: Page) => {
  await page.getByRole("tab", { name: "General Badge" }).click();
  await expect(page.getByText("LicenseNo less than 1 items")).toBeVisible();
};
const noContributorSelector = async (page: Page) => {
  await expect(
    page.getByRole("tab", { name: "Dandiset contributors Badge" })
  ).toBeVisible();
};
const invalidLicenseSelector = async (page: Page) => {
  await page.getByRole("tab", { name: "General Badge" }).click();
  await expect(
    page.getByRole("button", { name: "License spdx:CC-BY-NC-" })
  ).toBeVisible();
};
const titleTooLongSelector = async (page: Page) => {
  await page.getByRole("tab", { name: "General Badge" }).click();
  await expect(
    page.getByText("Dandiset title150 characters maximum")
  ).toBeVisible();
};

const allDandisets = [
  "000003",
  "000004",
  "000005",
  "000006",
  "000007",
  "000008",
  "000009",
  "000010",
  "000011",
  "000012",
  "000013",
  "000015",
  "000016",
  "000017",
  "000018",
  "000019",
  "000020",
  "000021",
  "000022",
  "000023",
  "000024",
  "000025",
  "000026",
  "000027",
  "000028",
  "000029",
  "000030",
  "000031",
  "000032",
  "000033",
  "000034",
  "000035",
  "000036",
  "000037",
  "000038",
  "000039",
  "000040",
  "000041",
  "000042",
  "000043",
  "000044",
  "000045",
  "000046",
  "000047",
  "000048",
  "000049",
  "000050",
  "000051",
  "000052",
  "000053",
  "000054",
  "000055",
  "000056",
  "000058",
  "000059",
  "000060",
  "000061",
  "000063",
  "000064",
  "000065",
  "000066",
  "000067",
  "000068",
  "000070",
  "000071",
  "000072",
  "000105",
  "000106",
  "000107",
  "000108",
  "000109",
  "000111",
  "000112",
  "000113",
  "000114",
  "000115",
  "000116",
  "000117",
  "000118",
  "000120",
  "000121",
  "000122",
  "000123",
  "000124",
  "000125",
  "000126",
  "000127",
  "000128",
  "000129",
  "000130",
  "000131",
  "000132",
  "000133",
  "000134",
  "000135",
  "000136",
  "000137",
  "000138",
  "000139",
  "000140",
  "000141",
  "000142",
  "000143",
  "000144",
  "000145",
  "000146",
  "000147",
  "000148",
  "000149",
  "000150",
  "000151",
  "000153",
  "000154",
  "000155",
  "000156",
  "000157",
  "000158",
  "000159",
  "000160",
  "000161",
  "000162",
  "000163",
  "000164",
  "000165",
  "000166",
  "000167",
  "000168",
  "000169",
  "000170",
  "000171",
  "000172",
  "000173",
  "000206",
  "000207",
  "000208",
  "000209",
  "000210",
  "000211",
  "000212",
  "000213",
  "000214",
  "000215",
  "000216",
  "000217",
  "000218",
  "000219",
  "000220",
  "000221",
  "000222",
  "000223",
  "000225",
  "000226",
  "000227",
  "000228",
  "000229",
  "000230",
  "000231",
  "000232",
  "000233",
  "000235",
  "000236",
  "000237",
  "000238",
  "000239",
  "000241",
  "000243",
  "000244",
  "000245",
  "000246",
  "000247",
  "000248",
  "000249",
  "000250",
  "000251",
  "000252",
  "000253",
  "000255",
  "000288",
  "000290",
  "000292",
  "000293",
  "000294",
  "000295",
  "000296",
  "000297",
  "000298",
  "000299",
  "000301",
  "000302",
  "000335",
  "000337",
  "000338",
  "000339",
  "000340",
  "000341",
  "000343",
  "000346",
  "000347",
  "000348",
  "000349",
  "000350",
  "000351",
  "000359",
  "000362",
  "000363",
  "000364",
  "000397",
  "000398",
  "000399",
  "000400",
  "000401",
  "000402",
  "000404",
  "000405",
  "000406",
  "000409",
  "000410",
  "000411",
  "000444",
  "000445",
  "000447",
  "000448",
  "000449",
  "000451",
  "000452",
  "000454",
  "000456",
  "000457",
  "000458",
  "000461",
  "000462",
  "000463",
  "000465",
  "000466",
  "000467",
  "000468",
  "000469",
  "000470",
  "000472",
  "000473",
  "000474",
  "000476",
  "000478",
  "000479",
  "000480",
  "000481",
  "000482",
  "000483",
  "000487",
  "000488",
  "000489",
  "000490",
  "000491",
  "000492",
  "000529",
  "000530",
  "000532",
  "000534",
  "000535",
  "000536",
  "000537",
  "000538",
  "000539",
  "000540",
  "000541",
  "000542",
  "000543",
  "000544",
  "000545",
  "000546",
  "000547",
  "000548",
  "000549",
  "000550",
  "000552",
  "000554",
  "000555",
  "000556",
  "000557",
  "000558",
  "000559",
  "000560",
  "000564",
  "000565",
  "000566",
  "000567",
  "000568",
  "000569",
  "000570",
  "000571",
  "000572",
  "000574",
  "000575",
  "000576",
  "000577",
  "000579",
  "000582",
  "000615",
  "000618",
  "000619",
  "000623",
  "000624",
  "000625",
  "000626",
  "000628",
  "000629",
  "000630",
  "000631",
  "000632",
  "000633",
  "000634",
  "000635",
  "000636",
  "000637",
  "000638",
  "000640",
  "000673",
  "000674",
  "000676",
  "000677",
  "000678",
  "000679",
  "000680",
  "000682",
  "000683",
  "000686",
  "000687",
  "000688",
  "000689",
  "000691",
  "000692",
  "000693",
  "000694",
  "000695",
  "000696",
  "000710",
  "000711",
  "000712",
  "000713",
  "000714",
  "000715",
  "000717",
  "000718",
  "000719",
  "000722",
  "000723",
  "000724",
  "000726",
  "000727",
  "000728",
  "000730",
  "000732",
  "000733",
  "000766",
  "000768",
  "000769",
  "000776",
  "000784",
  "000871",
  "000872",
  "000875",
  "000876",
  "000877",
  "000878",
  "000880",
  "000881",
  "000886",
  "000887",
  "000891",
  "000893",
];

const invalidDandisets = {
  "000018": [noLicenseSelector],
  "000021": [noLicenseSelector],
  "000022": [noLicenseSelector],
  "000024": [noContributorSelector, noLicenseSelector],
  "000028": [noContributorSelector, noLicenseSelector],
  "000030": [noContributorSelector, noLicenseSelector],
  "000031": [noContributorSelector, noLicenseSelector],
  "000033": [noContributorSelector, noLicenseSelector],
  "000038": [noContributorSelector, noLicenseSelector],
  "000042": [noContributorSelector, noLicenseSelector],
  "000046": [noContributorSelector, noLicenseSelector],
  "000047": [noContributorSelector, noLicenseSelector],
  "000050": [noContributorSelector, noLicenseSelector],
  "000051": [noContributorSelector, noLicenseSelector],
  "000052": [noContributorSelector, noLicenseSelector],
  "000060": [noLicenseSelector],
  "000063": [noContributorSelector, noLicenseSelector],
  "000068": [noContributorSelector, noLicenseSelector],
  "000071": [noContributorSelector],
  "000072": [noContributorSelector, noLicenseSelector],
  "000106": [invalidLicenseSelector],
  "000107": [invalidLicenseSelector, noContributorSelector],
  "000112": [noContributorSelector, noLicenseSelector],
  "000113": [noContributorSelector, noLicenseSelector],
  "000116": [noLicenseSelector],
  "000120": [noLicenseSelector],
  "000124": [noLicenseSelector],
  "000131": [noLicenseSelector],
  "000132": [noLicenseSelector],
  "000133": [noLicenseSelector],
  "000134": [noLicenseSelector],
  "000135": [noLicenseSelector],
  "000136": [noLicenseSelector],
  "000137": [noLicenseSelector],
  "000141": [invalidLicenseSelector],
  "000144": [noLicenseSelector],
  "000145": [noLicenseSelector],
  "000146": [noLicenseSelector],
  "000150": [noLicenseSelector],
  "000151": [noLicenseSelector],
  "000155": [noLicenseSelector],
  "000157": [noLicenseSelector],
  "000158": [noLicenseSelector],
  "000160": [noLicenseSelector],
  "000162": [noLicenseSelector],
  "000164": [noLicenseSelector],
  "000170": [noLicenseSelector],
  "000171": [noLicenseSelector],
  "000208": [noLicenseSelector],
  "000210": [noLicenseSelector],
  "000214": [noLicenseSelector],
  "000216": [noLicenseSelector],
  "000225": [noLicenseSelector],
  "000227": [noLicenseSelector],
  "000229": [noLicenseSelector],
  "000255": [noLicenseSelector],
  "000290": [noLicenseSelector],
  "000362": [titleTooLongSelector],
  "000449": [noLicenseSelector],
  "000534": [noContributorSelector],
};

test.describe("Test meditor validation errors", async () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(clientUrl);
    await page.getByRole("button", { name: "Log In with GitHub" }).click();
    await page.getByPlaceholder("Email address").click();
    await page.getByPlaceholder("Email address").fill("admin@kitware.com");
    await page.getByPlaceholder("Password").click();
    await page.getByPlaceholder("Password").fill("password");
    await page.getByRole("button", { name: "Sign In " }).click();
    await page.waitForLoadState("networkidle");
  });

  for (const dandisetId of allDandisets) {
    test(`Test dandiset ${dandisetId}`, async ({ page }) => {
      await page.goto(`${clientUrl}/#/dandiset/${dandisetId}/draft/`);
      await page.getByRole("button", { name: "Metadata" }).click();

      await page.getByLabel("Dandiset title").click();
      await page.keyboard.press("End");
      await page.keyboard.press("Space");
      await page.keyboard.press("Tab");
      await page.getByLabel("Dandiset title").click();
      await page.keyboard.press("End");
      await page.keyboard.press("Backspace");
      await page.keyboard.press("Tab");
      await page.locator(".v-card__actions > button").first().click();
      await page.waitForTimeout(3000);
      await page.waitForLoadState("networkidle");

      const validIcon = await page.locator(".v-card__actions > i");
      const iconClass = await validIcon.getAttribute("class");

      if (Object.keys(invalidDandisets).includes(dandisetId)) {
        expect(iconClass).toContain("mdi-alert-circle");
        const tests = invalidDandisets[dandisetId];
        for (const test of tests) {
          await test(page);
        }
      } else {
        expect(iconClass).toContain("mdi-checkbox-marked-circle");
      }
    });
  }
});
