from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyppeteer.page import Page


async def wait_for_navigation(page: Page):
    """
    Wait for all pending network requests to finish.

    Note, sometimes the Sentry client SDK causes this to hang until it times out.
    To counter this, set a hard limit to the timeout and suppress any errors
    that occur because of it.
    """
    from pyppeteer.errors import TimeoutError

    try:
        await page.waitForNavigation({'waitUntil': 'networkidle0', 'timeout': 5000})
    except TimeoutError:
        pass


async def disable_all_cookies(page: Page):
    """Disable cookies in the pyppeteer browser."""
    client = await page.target.createCDPSession()
    await client.send('Emulation.setDocumentCookieDisabled', {'disabled': True})
    await page.reload()
    await wait_for_navigation(page)


async def contains_text(page: Page, text: str):
    """Determine if the given page contains the given text."""
    from pyppeteer.errors import TimeoutError

    try:
        await page.waitForXPath(f'//*[contains(., "{text}")]', {'timeout': 500})
        return True
    except TimeoutError:
        return False
