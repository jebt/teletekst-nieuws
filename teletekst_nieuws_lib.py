from setup_logger import log
from story import Story


def get_new_browser():
    log("Instantiating new headless firefox browser...")
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.remote.remote_connection import LOGGER as SELENIUM_LOGGER
    from urllib3.connectionpool import log as urllib_logger
    from shutil import which
    from selenium import webdriver
    from logging import WARNING
    options = Options()
    options.headless = True
    options.binary = which("firefox")
    SELENIUM_LOGGER.setLevel(WARNING)
    urllib_logger.setLevel(WARNING)
    new_browser = webdriver.Firefox(options=options)
    return new_browser


def is_subset(newly_scraped_stories: dict, previously_scraped_stories: dict):
    for new_title, new_story in newly_scraped_stories.items():
        if new_title not in previously_scraped_stories:
            return False
        else:
            old_story = previously_scraped_stories[new_title]
            if new_story != old_story:
                return False
    return True


def is_short_story_page(text: str) -> bool:
    return "kort nieuws" in Story(raw_text=text, page=0).title.lower()


def split_short_stories_text(text: str) -> list[str]:
    closer = ""
    split = text.split("")
    short_story_texts = []
    for i in range(len(split) - 1):
        text = "".join([split[0], "", split[i + 1]]) + closer
        short_story_texts.append(text)
    return short_story_texts
