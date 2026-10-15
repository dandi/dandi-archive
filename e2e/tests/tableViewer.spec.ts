import { test, expect, type Page } from "@playwright/test";
import { clientUrl } from "../utils.ts";

/**
 * Tests for the table viewer, which displays .tsv/.csv assets in the file
 * browser instead of handing them to the browser as a download.
 *
 * The viewer needs a tabular asset and, unlike every other page, needs that
 * asset's *contents*. The playwright fixture has neither: its only asset is
 * `foo/bar.txt`, and the blob it points at has no object in storage, since the
 * fixture restores the database and not the bucket. These tests therefore serve
 * the asset listing and the asset's bytes themselves, and leave the rest of the
 * page -- the dandiset, its versions, its owners -- to the API server, as the
 * other specs do. Everything they assert on is client side: the row links, the
 * dialog, the parsing, the guardrails and the URL handling.
 */

const dandisetId = "000003";
const dandisetVersion = "draft";
const filesUrl = `${clientUrl}/dandiset/${dandisetId}/${dandisetVersion}/files`;

const TSV_ASSET_ID = "11111111-1111-1111-1111-111111111111";
const TXT_ASSET_ID = "22222222-2222-2222-2222-222222222222";
// Where the listing says the tabular asset's bytes live. The viewer fetches
// this directly for a dandiset that isn't embargoed, exactly as the "Open With"
// services do.
const TSV_BLOB_URL = "http://localhost:9000/django-storage-testing/blobs/data.tsv";

const TSV = [
  "subject\tsession\tnotes\treference",
  "sub-01\tses-1\tfirst session\thttps://example.com/sub-01",
  "sub-02\tses-1\tsecond session\thttps://example.com/sub-02",
].join("\n");

// One more row than the viewer will render, so the table is truncated.
const MAX_ROWS = 5000;
const LONG_TSV = ["subject\tvalue"]
  .concat(Array.from({ length: MAX_ROWS }, (_, i) => `sub-${i}\t${i}`))
  .join("\n");

// The quote opened in the second field is never closed, which makes everything
// after it one enormous cell.
const MALFORMED_TSV = [
  "subject\tnotes",
  'sub-01\t"unclosed',
  "sub-02\tsecond",
].join("\n");

const timestamps = { created: "2024-02-17T18:00:59.741Z", modified: "2024-02-17T18:00:59.741Z" };

function assetPath(path: string, assetId: string | null, size: number, url = "") {
  return {
    ...timestamps,
    path,
    version: 1,
    aggregate_files: 1,
    aggregate_size: size,
    asset: assetId ? { asset_id: assetId, url } : null,
  };
}

/**
 * Serve a listing holding a tabular asset, a non-tabular one and a folder, so
 * that each kind of row can be compared against the others.
 */
async function stubListing(page: Page, options: { tsvSize?: number } = {}) {
  await page.route(/\/assets\/paths\//, (route) => route.fulfill({
    json: {
      count: 3,
      next: null,
      previous: null,
      results: [
        assetPath("sub-01", null, 100),
        assetPath("data.tsv", TSV_ASSET_ID, options.tsvSize ?? TSV.length, TSV_BLOB_URL),
        assetPath("notes.txt", TXT_ASSET_ID, 20, "http://localhost:9000/blobs/notes.txt"),
      ],
    },
  }));
}

/** Report this dandiset as embargoed, whatever the API server says. */
async function stubEmbargoed(page: Page) {
  await page.route(/\/versions\/[^/]+\/info\/$/, async (route) => {
    const response = await route.fetch();
    const version = await response.json();
    version.dandiset.embargo_status = "EMBARGOED";
    return route.fulfill({ response, json: version });
  });
}

/** Serve the tabular asset's bytes, from wherever the viewer asks for them. */
async function stubContent(page: Page, body: string) {
  await page.route(
    (url) => url.href.includes("/blobs/data.tsv")
      || /\/assets\/[^/]+\/download/.test(url.href),
    (route) => route.fulfill({ body, contentType: "text/tab-separated-values" }),
  );
}

const dialog = (page: Page) => page.locator(".v-dialog .v-card");
const closeViewer = (page: Page) => dialog(page).getByRole("button").filter({ has: page.locator(".mdi-close") }).click();

test.describe("Table viewer", () => {
  test("a tabular asset's row links to the viewer, and other rows keep their own links", async ({ page }) => {
    await stubListing(page);
    await stubContent(page, TSV);
    await page.goto(filesUrl);

    // The tabular row is a router link to the viewer rather than a link to the
    // raw asset, so it has no href of its own.
    const tabularRow = page.getByRole("link", { name: "data.tsv" });
    await expect(tabularRow).toHaveAttribute("href", /table=data\.tsv/);

    // Everything else is untouched: other assets still open raw, and folders
    // still navigate into the listing.
    await expect(page.getByRole("link", { name: "notes.txt" }))
      .toHaveAttribute("href", new RegExp(`assets/${TXT_ASSET_ID}/download`));
    await expect(page.getByRole("link", { name: "sub-01" }))
      .toHaveAttribute("href", /location=sub-01/);
  });

  test("clicking a tabular asset opens it as a table, and the URL says so", async ({ page }) => {
    await stubListing(page);
    await stubContent(page, TSV);
    await page.goto(filesUrl);
    await page.getByRole("link", { name: "data.tsv" }).click();

    await expect(dialog(page)).toBeVisible();
    await expect(dialog(page)).toContainText("data.tsv");
    // The first row of the file is the header row, and the rest are the data.
    await expect(dialog(page).getByRole("columnheader", { name: "subject" })).toBeVisible();
    await expect(dialog(page).getByRole("columnheader", { name: "session" })).toBeVisible();
    await expect(dialog(page).getByRole("cell", { name: "first session" })).toBeVisible();
    await expect(dialog(page)).toContainText("2 rows × 4 columns");
    expect(page.url()).toContain("table=data.tsv");
  });

  test("a cell holding a URL is rendered as a link", async ({ page }) => {
    await stubListing(page);
    await stubContent(page, TSV);
    await page.goto(`${filesUrl}?table=data.tsv`);

    await expect(dialog(page).getByRole("link", { name: "https://example.com/sub-01" }))
      .toHaveAttribute("href", "https://example.com/sub-01");
  });

  test("the raw text view shows the file as it is", async ({ page }) => {
    await stubListing(page);
    await stubContent(page, TSV);
    await page.goto(`${filesUrl}?table=data.tsv`);
    await dialog(page).getByRole("button").filter({ has: page.locator(".mdi-file-document-outline") }).click();

    await expect(dialog(page).locator("pre")).toContainText("subject\tsession");
  });

  test("the row's buttons act on the asset instead of opening the viewer", async ({ page }) => {
    await stubListing(page);
    await stubContent(page, TSV);
    await page.goto(filesUrl);

    // The download request is answered with an abort, so that the browser stays
    // on the file browser and the assertions below can still see it.
    const downloads: string[] = [];
    await page.route(/\/assets\/[^/]+\/download\/$/, (route) => {
      downloads.push(route.request().url());
      return route.abort();
    });

    // The download button sits inside the row, which is a link to the viewer
    // for a tabular asset: its click must not be taken for a click on the row.
    // The button carries an href, so Vuetify renders it as a link, not a button.
    const row = page.locator(".v-list-item").filter({ hasText: "data.tsv" });
    await row.locator(".v-btn").filter({ has: page.locator(".mdi-download") }).click();

    await expect.poll(() => downloads).toHaveLength(1);
    expect(downloads[0]).toContain(`assets/${TSV_ASSET_ID}/download/`);
    await expect(dialog(page)).toBeHidden();
    expect(page.url()).not.toContain("table=");
  });

  test("a link straight into the viewer opens it, and closing returns to the listing", async ({ page }) => {
    await stubListing(page);
    await stubContent(page, TSV);
    await page.goto(`${filesUrl}?table=data.tsv`);
    await expect(dialog(page)).toBeVisible();

    await closeViewer(page);

    await expect(dialog(page)).toBeHidden();
    expect(page.url()).not.toContain("table=");
    await expect(page.getByRole("link", { name: "data.tsv" })).toBeVisible();
  });

  test("the browser's back button closes the viewer", async ({ page }) => {
    await stubListing(page);
    await stubContent(page, TSV);
    await page.goto(filesUrl);
    await page.getByRole("link", { name: "data.tsv" }).click();
    await expect(dialog(page)).toBeVisible();

    await page.goBack();

    await expect(dialog(page)).toBeHidden();
    expect(page.url()).not.toContain("table=");
  });

  test("a file with more rows than the viewer shows is truncated, with a notice", async ({ page }) => {
    await stubListing(page);
    await stubContent(page, LONG_TSV);
    await page.goto(`${filesUrl}?table=data.tsv`);

    await expect(dialog(page)).toContainText(`only the first ${MAX_ROWS} rows are shown`);
  });

  test("a file whose quoted field is never closed is shown with a warning", async ({ page }) => {
    await stubListing(page);
    await stubContent(page, MALFORMED_TSV);
    await page.goto(`${filesUrl}?table=data.tsv`);

    await expect(dialog(page)).toContainText("never closed");
  });

  test("a file too large to preview is not fetched at all", async ({ page }) => {
    let requested = false;
    await stubListing(page, { tsvSize: 60e6 });
    await page.route(
      (url) => url.href.includes("/blobs/data.tsv"),
      (route) => { requested = true; return route.fulfill({ body: TSV }); },
    );
    await page.goto(`${filesUrl}?table=data.tsv`);

    await expect(dialog(page)).toContainText("too large to preview");
    expect(requested).toBe(false);
  });

  test("an embargoed asset is fetched through the API rather than its S3 URL", async ({ page }) => {
    const fetched: string[] = [];
    await stubListing(page);
    await stubEmbargoed(page);
    await page.route(
      (url) => url.href.includes("/blobs/data.tsv")
        || /\/assets\/[^/]+\/download/.test(url.href),
      (route) => {
        fetched.push(route.request().url());
        return route.fulfill({ body: TSV, contentType: "text/tab-separated-values" });
      },
    );
    await page.goto(`${filesUrl}?table=data.tsv`);

    // The ready-made S3 URL denies access for an embargoed asset, so the viewer
    // has to ask the API, which is the request that carries the user's
    // credentials.
    await expect(dialog(page).getByRole("columnheader", { name: "subject" })).toBeVisible();
    expect(fetched).toHaveLength(1);
    expect(fetched[0]).toContain(`assets/${TSV_ASSET_ID}/download`);
    expect(fetched[0]).not.toContain("/blobs/");
  });
});
