from time import sleep

from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from constants import SELECTOR_PAGE, START_FROM_PAGE, SELECTOR_NEXT
from setup_logger import logger, log


class PageLoader:
    def __init__(self, browser, page):
        self.browser = browser
        self.page = page
        self.prev_page = page
        self.dots = 1

    def load_next_page(self):
        self.try_get_page()
        if self.page == self.prev_page:
            print(".", end="")
            self.dots += 1
            if self.dots % 200 == 0:
                logger.error(f"{self.dots=}, {self.page=}")
                log(f"Reloading the first story page... ({START_FROM_PAGE=})")
                self.browser.get(f"https://nos.nl/teletekst#{START_FROM_PAGE}")
                sleep(1)
            if self.dots % 20 == 0:
                logger.warning(f"{self.dots=}, {self.page=}")
                self.try_click_next()
            sleep(0.1)

    def try_get_page(self):
        try:
            elem = self.browser.find_element(by=By.CSS_SELECTOR, value=SELECTOR_PAGE)
            self.page = int(elem.text)
        except StaleElementReferenceException:
            print("E", end="\n")
            logger.debug("StaleElementReferenceException")
        except NoSuchElementException:
            print("E", end="\n")
            logger.warning("NoSuchElementException")

    def try_click_next(self):
        try:
            next_button = self.browser.find_element(by=By.CSS_SELECTOR, value=SELECTOR_NEXT)
            next_button.click()
        except NoSuchElementException:
            logger.error("NoSuchElementException")
            log(f"Reloading the page... ({self.page=})")
            self.browser.get(f"https://nos.nl/teletekst#{self.page}")
            sleep(0.5)
