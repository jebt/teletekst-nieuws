import logging

import selenium

from constants import START_FROM_PAGE, SELECTOR_NEXT
from page_loader import PageLoader
from publisher import Publisher
from setup_logger import logger, log
import os
import datetime
import time
import json
import snapshot

from story import Story
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.remote_connection import LOGGER as SELENIUM_LOGGER
from urllib3.connectionpool import log as urllib_logger
from shutil import which, move

# todo: handle multiple "kort nieuws binnenland/buitenland" stories. (list in dict?)
# todo: swap files system for database (sqlite)
# todo: every archive size number of snapshots make a meta snapshot of the last archive to check old stories
#  then we can use the last archive(s) plus the pre-archive to make the merged dict to check against and we don't
#  have to keep extra dicts in the fresh folder.
# todo: make the merged dict based on time instead of count (e.g. all (meta-)dicts from within the last 48 hours)
# todo: if a minor change is made to a story, make an edit to the telegram, reddit(,etc) posts.
#  for reddit it might be preferable to edit over repost even if the change is major! for telegram the levenshtein
#  distance threshold for major changes could be raised along with this.
# todo: add reddit publisher bot in it's own sub
# todo: break up into classes/modules and make more object oriented

# todo: lengthen the sleep times.

# todo: everything to the cloud (google?) (automatically pick up the code from github)

# todo: if every essential feature and bugfixes are done and the bot is running in the cloud smoothly for a while,
#  create new telegram channel and identity for the bot and invite people.

abort = False
publish_all_current = False
ROLLING_SNAPSHOTS_WINDOW_SIZE = 1000
SNAPSHOTS_ARCHIVE_SIZE = 1000
SELECTOR_CONTENT = "#teletekst > div.teletekst__content.js-tt-content > pre"


def main():
    global abort
    log("########## START ##########\n")

    browser = get_browser()
    cycle_counter = 0
    while not abort:
        cycle_counter += 1
        log(f"Cycle {cycle_counter}...")
        bot_cycle(browser)

    browser.quit()
    log("########## END ##########\n")


def get_browser():
    options = Options()
    options.headless = True
    options.binary = which("firefox")
    SELENIUM_LOGGER.setLevel(logging.WARNING)
    urllib_logger.setLevel(logging.WARNING)
    browser = webdriver.Firefox(options=options)
    return browser


def bot_cycle(browser):  # todo: tests and make flow more readable (extract functions, add comments)
    global publish_all_current

    # data operations
    snapshots = os.listdir("snapshots")
    if len(snapshots) > (SNAPSHOTS_ARCHIVE_SIZE + ROLLING_SNAPSHOTS_WINDOW_SIZE):
        archive_old_snapshots(snapshots)

    previously_scraped_stories = get_merged_title_body_map()

    # scraping
    fresh_snapshot_obj = scrape_snapshot(browser)
    fresh_title_body_map = fresh_snapshot_obj.get_title_body_map()
    save_stories(fresh_title_body_map)
    log(f"{len(fresh_title_body_map)=}")

    # publishing
    publisher = Publisher(previously_scraped_stories, fresh_snapshot_obj)
    if publish_all_current:
        publisher.publish(scope="current")
        publish_all_current = False
    else:
        publisher.publish(scope="new_and_major_updates")


def archive_old_snapshots(snapshots: list[str]):
    snapshots.sort()
    time_string = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs(f"snapshots_archive/{time_string}", exist_ok=True)
    for file in snapshots[:SNAPSHOTS_ARCHIVE_SIZE]:
        # move file to new directory
        move(f"snapshots/{file}", f"snapshots_archive/{time_string}/{file}")


def scrape_snapshot(browser) -> snapshot:  # todo: refactor
    fresh_snapshot_obj = snapshot.Snapshot()
    page = load_first_page(browser)

    # getting the stories
    while page < 200:
        logging.debug(f"{page=}")
        print(f"{page}", end=".")
        text = try_get_text(browser)
        if not text:
            time.sleep(0.1)
            continue
        story = Story(raw_text=text, page=page)
        fresh_snapshot_obj.add_story(story)

        next_button = browser.find_element(by=By.CSS_SELECTOR, value=SELECTOR_NEXT)
        next_page = int(next_button.get_attribute("href").split("#")[1])
        if next_page >= 200:
            print("done")
            log(f"{next_page=}, breaking out of next page looping...")
            unique_story_count = fresh_snapshot_obj.get_unique_title_count()
            if unique_story_count <= 1:
                logging.error(f"{next_page=} while {unique_story_count=}!")
            break

        next_button.click()
        time.sleep(0.1)
        page_loader = PageLoader(browser, page)
        while page_loader.page == page_loader.prev_page:
            page_loader.load_next_page()

        page = page_loader.page

    # finalizing the scraping process
    if fresh_snapshot_obj.get_unique_title_count() < 1:
        logging.error("No stories found!")
    return fresh_snapshot_obj


def load_first_page(browser):
    log("Scraping stories...")
    page = 190
    try:
        browser.get(f"https://nos.nl/teletekst#{START_FROM_PAGE}")
    except selenium.common.exceptions.WebDriverException as e:
        logger.error(f"Could not load page! {e}")
    time.sleep(0.5)
    first_page_load_poll_tries = 0
    while page >= 190:
        first_page_load_poll_tries += 1  # don't start at 0 because of modulo check
        page = poll_for_first_page_load(browser, page, first_page_load_poll_tries)
    return page


def poll_for_first_page_load(browser, page, polling_tries):
    if polling_tries % 10 == 0:
        logging.warning(f"{polling_tries=}, {page=}, getting {START_FROM_PAGE}...")
        browser.get(f"https://nos.nl/teletekst#{START_FROM_PAGE}")
        time.sleep(1)
    page_loader = PageLoader(browser, page)
    page_loader.try_get_page()
    if page_loader.page >= 190:
        print(f"{page_loader.page=}")
        time.sleep(0.1)
    return page_loader.page


def try_get_text(browser):
    text = None
    try:
        text = browser.find_element(by=By.CSS_SELECTOR, value=SELECTOR_CONTENT).text
    except StaleElementReferenceException:
        log("StaleElementReferenceException")
    return text


def load_snapshot_by_sorted_files_index(index: int) -> dict:
    files = os.listdir("snapshots")
    files.sort()
    file = files[index]
    with open(f"snapshots/{file}", "r") as f:
        saved_stories = json.load(f)
    log(f"Loaded {len(saved_stories)} stories from {file}")
    return saved_stories


def get_merged_title_body_map() -> dict:
    title_body_maps = load_list_of_last_story_snapshots(ROLLING_SNAPSHOTS_WINDOW_SIZE)
    merged_title_body_map = {}
    for title_body_map in title_body_maps:
        merged_title_body_map.update(title_body_map)
    return merged_title_body_map


def load_list_of_last_story_snapshots(how_many_if_available: int) -> list:
    files = os.listdir("snapshots")
    files.sort()
    if len(files) > how_many_if_available:
        files = files[-how_many_if_available:]
    snapshots = []
    for file in files:
        with open(f"snapshots/{file}", "r") as f:
            snapshots.append(json.load(f))
    log(f"Loaded last {len(snapshots)} snapshots")
    return snapshots


def save_stories(stories: dict):
    time_string = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs("snapshots", exist_ok=True)
    with open(f"snapshots/{time_string}.json", "w") as f:
        json.dump(stories, f, indent=4)


if __name__ == "__main__":
    main()
