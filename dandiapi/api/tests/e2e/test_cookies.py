from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyppeteer.page import Page

import pytest
from utils import contains_text, disable_all_cookies

COOKIE_CONSENT_MESSAGE = 'We use cookies to ensure you get the best experience on DANDI.'
COOKIE_DISABLED_MESSAGE = (
    "We noticed you're blocking cookies - note that certain aspects of the site may not work."
)


@pytest.mark.pyppeteer
async def test_cookies_acknowledgement_banner(page: Page):
    # Ensure page contains cookie acknowledgement banner
    assert await contains_text(page, COOKIE_CONSENT_MESSAGE)

    # Click cookie acknowledgement banner
    await page.click('button.Cookie__button')

    # Give banner 500ms to disappear
    await page.waitFor(500)

    # Ensure that the banner went away after clicking
    assert not await contains_text(page, COOKIE_CONSENT_MESSAGE)


@pytest.mark.pyppeteer
async def test_cookies_disabled_banner(page: Page):
    await disable_all_cookies(page)

    # Ensure the page shows a message warning the user that they have cookies disabled
    assert await contains_text(page, COOKIE_DISABLED_MESSAGE)
