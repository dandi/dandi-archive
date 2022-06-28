from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyppeteer.page import Page
    from pyppeteer.element_handle import ElementHandle

import pytest
from utils import contains_text, wait_for_navigation

from dandiapi.api.models import Version


@pytest.mark.pyppeteer
@pytest.mark.django_db
async def test_search(
    page: Page,
    webpack_server: str,
    published_version_factory,
    asset_factory,
):
    # Create some dandisets with assets
    dandisets: list[Version] = [published_version_factory() for _ in range(20)]
    for dandiset in dandisets:
        asset = asset_factory()
        asset.versions.set([dandiset])

    # Search for each of them using the search bar and ensure they are in the results
    for dandiset in dandisets:
        await page.goto(f'{webpack_server}dandiset/search')
        await wait_for_navigation(page)
        search_bar: ElementHandle = await page.waitForXPath(
            '//*[contains(concat(" ",@class," "), " v-text-field ")][.//*[label[contains(text(),'
            '"Search Dandisets by name, description, identifier, or contributor name")]]]//input'
        )

        await search_bar.focus()
        await page.keyboard.type(dandiset.name)
        await page.keyboard.press('Enter')
        await wait_for_navigation(page)

        assert await contains_text(page, dandiset.name)
