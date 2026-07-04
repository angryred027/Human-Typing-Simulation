from __future__ import annotations

import time
import asyncio
from typing import Any

from .typer import MarkovTyper


def _extract_char(action: str) -> str:
    """Extract the typed character(s) from an action string like TYPED 'x' or TYPED_SWAP 'ht'."""
    first_quote = action.index("'")
    last_quote = action.rindex("'")
    return action[first_quote + 1:last_quote]


class HumanTyper:
    """
    A helper class to integrate realistic typing into automation frameworks
    like Playwright, Selenium, or Appium.
    """

    def __init__(self, wpm: float = 60.0, layout: str = "qwerty") -> None:
        if not isinstance(wpm, (int, float)) or wpm <= 0:
            raise ValueError("wpm must be a positive number")
        self.wpm = wpm
        self.layout = layout

    async def type(self, page_element: Any, text: str) -> None:
        """
        Types text into a Playwright element with realistic human behavior.

        This is the main method for Playwright integration. It simulates:
        - Variable typing speed based on word complexity
        - Realistic errors (neighbor keys, swaps)
        - Natural corrections with backspace
        - Fatigue over longer texts

        Args:
            page_element: The Playwright Locator or ElementHandle to type into.
            text: The text to type with human-like behavior.

        Example:
            typer = HumanTyper(wpm=70)
            input_box = page.locator("input[name='search']")
            await input_box.click()
            await typer.type(input_box, "Hello world!")
        """
        if not isinstance(text, str) or len(text) == 0:
            raise ValueError("text must be a non-empty string")

        typer = MarkovTyper(text, target_wpm=self.wpm, layout=self.layout)
        _, history = typer.run()

        last_time = 0.0

        for t, action, _ in history:
            delay = t - last_time
            if delay > 0:
                await asyncio.sleep(delay)
            last_time = t

            if "BACKSPACE" in action:
                await page_element.press("Backspace")
            elif "TYPED_SWAP" in action or "TYPED_DOUBLE" in action:
                for char in _extract_char(action):
                    await page_element.press(char)
            elif "TYPED_ERROR" in action:
                char = _extract_char(action)
                await page_element.press(char)
            elif "TYPED" in action:
                char = _extract_char(action)
                await page_element.press(char)

    def type_appium(self, driver: Any, text: str) -> None:
        """
        Types text into the focused mobile element using W3C Actions.
        This operates at the driver level and requires the element to be focused.

        Args:
            driver: The Appium WebDriver.
            text: The text to type.

        Example:
            typer = HumanTyper(wpm=45)
            search_box = driver.find_element(...)
            search_box.click()  # Ensure focus
            typer.type_appium(driver, "Hello Appium")
        """
        if not isinstance(text, str) or len(text) == 0:
            raise ValueError("text must be a non-empty string")

        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.keys import Keys

        typer = MarkovTyper(text, target_wpm=self.wpm, layout=self.layout)
        _, history = typer.run()

        last_time = 0.0

        for t, action, _ in history:
            delay = t - last_time
            if delay > 0:
                time.sleep(delay)
            last_time = t

            actions = ActionChains(driver)
            if "BACKSPACE" in action:
                actions.send_keys(Keys.BACK_SPACE).perform()
            elif "TYPED_SWAP" in action or "TYPED_DOUBLE" in action:
                for char in _extract_char(action):
                    actions.send_keys(char)
                actions.perform()
            elif "TYPED" in action:  # Handles TYPED, TYPED_ERROR
                char = _extract_char(action)
                actions.send_keys(char).perform()

    def type_sync(self, selenium_element: Any, text: str) -> None:
        """
        Types text into a Selenium WebElement with realistic human behavior.

        Args:
            selenium_element: The Selenium WebElement to type into.
            text: The text to type with human-like behavior.

        Example:
            typer = HumanTyper(wpm=65)
            input_box = driver.find_element(By.NAME, "search")
            input_box.click()
            typer.type_sync(input_box, "Hello Selenium!")
        """
        if not isinstance(text, str) or len(text) == 0:
            raise ValueError("text must be a non-empty string")

        from selenium.webdriver.common.keys import Keys

        typer = MarkovTyper(text, target_wpm=self.wpm, layout=self.layout)
        _, history = typer.run()

        last_time = 0.0

        for t, action, _ in history:
            delay = t - last_time
            if delay > 0:
                time.sleep(delay)
            last_time = t

            if "BACKSPACE" in action:
                selenium_element.send_keys(Keys.BACK_SPACE)
            elif "TYPED_SWAP" in action or "TYPED_DOUBLE" in action:
                for char in _extract_char(action):
                    selenium_element.send_keys(char)
            elif "TYPED" in action:  # Handles TYPED, TYPED_ERROR
                char = _extract_char(action)
                selenium_element.send_keys(char)
