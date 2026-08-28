"""
Project-1 ChatGPT Browser Agent.

Browser-based bridge between the Project-1 orchestrator
and the ChatGPT web interface.

The agent intentionally does not store credentials,
cookies, browser profiles, screenshots, or authentication
data in the repository.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional


class ChatGPTBrowserAgent:
    """
    Minimal browser agent for communicating with ChatGPT.

    The Playwright Page object is supplied by the caller.
    """

    INPUT_SELECTORS = (
        "textarea",
        "[contenteditable='true']",
        "[role='textbox']",
    )

    CLOSE_SELECTORS = (
        "button[aria-label='Close']",
        "button[aria-label='Close dialog']",
        "button[aria-label='Dismiss']",
        "button:has-text('Close')",
        "button:has-text('Not now')",
        "button:has-text('Maybe later')",
    )

    def __init__(
        self,
        page,
        screenshot_dir: str | Path = "/content",
        response_timeout: int = 120,
        stable_seconds: int = 5,
    ):
        self.page = page
        self.screenshot_dir = Path(screenshot_dir)
        self.response_timeout = response_timeout
        self.stable_seconds = stable_seconds

    async def _close_popup(self) -> bool:
        """Close an obvious blocking dialog if one is present."""

        for selector in self.CLOSE_SELECTORS:

            try:
                locator = self.page.locator(selector)
                count = await locator.count()

                for index in range(count):

                    element = locator.nth(index)

                    try:
                        if await element.is_visible():
                            await element.click(timeout=2000)
                            await self.page.wait_for_timeout(500)
                            return True
                    except Exception:
                        pass

            except Exception:
                pass

        return False

    async def _find_input(self):
        """Find the visible ChatGPT message input."""

        for selector in self.INPUT_SELECTORS:

            try:
                locator = self.page.locator(selector)
                count = await locator.count()

                for index in range(count):

                    element = locator.nth(index)

                    try:
                        if await element.is_visible():
                            return element
                    except Exception:
                        pass

            except Exception:
                pass

        return None

    async def _wait_for_stable_page(self) -> str:
        """
        Wait until the visible page text stops changing.

        This is deliberately conservative. DOM-specific response
        extraction can be improved independently later.
        """

        start = time.time()

        last_text = ""
        stable_since: Optional[float] = None

        while time.time() - start < self.response_timeout:

            await self.page.wait_for_timeout(1000)

            try:
                text = await self.page.locator("body").inner_text()
            except Exception:
                text = ""

            if text != last_text:

                last_text = text
                stable_since = time.time()

            elif (
                stable_since is not None
                and time.time() - stable_since
                >= self.stable_seconds
            ):
                return text

        return last_text

    @staticmethod
    def _extract_answer_from_text(text: str) -> Optional[str]:
        """
        Conservative fallback extraction.

        The ChatGPT DOM changes over time, so this method intentionally
        avoids depending on undocumented internal class names.
        """

        ignored = {
            "New chat",
            "Search chats",
            "Images",
            "Plugins",
            "Deep research",
            "Settings",
            "Help",
            "Log in",
            "Sign up for free",
            "Chat with ChatGPT",
            "ChatGPT is AI and can make mistakes.",
        }

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        useful = [
            line
            for line in lines
            if line not in ignored
        ]

        for line in reversed(useful):

            if len(line) >= 30:
                return line

        return None

    async def ask(
        self,
        message: str,
        screenshot: bool = True,
    ) -> str:
        """
        Send a message to ChatGPT and return the extracted answer.
        """

        if self.page.is_closed():
            raise RuntimeError(
                "ChatGPT browser page is closed."
            )

        await self._close_popup()

        input_box = await self._find_input()

        if input_box is None:

            raise RuntimeError(
                "ChatGPT message input was not found."
            )

        await input_box.click()
        await input_box.fill(message)
        await input_box.press("Enter")

        text = await self._wait_for_stable_page()

        answer = self._extract_answer_from_text(text)

        if screenshot:

            self.screenshot_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            screenshot_path = (
                self.screenshot_dir
                / "project1_chatgpt_result.png"
            )

            await self.page.screenshot(
                path=str(screenshot_path),
                full_page=True,
            )

        if not answer:

            raise RuntimeError(
                "ChatGPT response was generated, "
                "but its text could not be isolated."
            )

        return answer
