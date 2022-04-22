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
from short_story import ShortStory

from story import Story
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from shutil import move
from teletekst_nieuws_lib import get_new_browser, is_short_story_page, split_short_stories_text

abort = False
publish_all_current = False
browser = get_new_browser()
ROLLING_SNAPSHOTS_WINDOW_SIZE = 1000
SNAPSHOTS_ARCHIVE_SIZE = 1000
SELECTOR_CONTENT = "#teletekst > div.teletekst__content.js-tt-content > pre"
RESTART_BROWSER_AFTER_CYCLES = 1000  # todo: make time based (once a day at 03:00 NL time?)


def main():
    log("########## START ##########\n")

    cycle_counter = 0
    while not abort:
        cycle_counter += 1
        if cycle_counter % RESTART_BROWSER_AFTER_CYCLES == 0:  # todo: make time based (once a day at 03:00 NL time?)
            restart_browser()
        log(f"Cycle {cycle_counter}...")
        bot_cycle()

    if browser is not None:
        browser.quit()
    log("########## END ##########\n")


def restart_browser():
    global browser
    if browser is not None:
        browser.quit()
    browser = get_new_browser()


def bot_cycle():  # todo: tests and make flow more readable (extract functions, add comments)
    global publish_all_current

    # data operations
    snapshots = os.listdir("snapshots")
    if len(snapshots) > (SNAPSHOTS_ARCHIVE_SIZE + ROLLING_SNAPSHOTS_WINDOW_SIZE):
        archive_old_snapshots(snapshots)

    previously_scraped_stories = get_merged_title_body_map()

    # scraping
    fresh_snapshot_obj = scrape_snapshot()
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


def scrape_snapshot() -> snapshot:  # todo: refactor
    fresh_snapshot_obj = snapshot.Snapshot()
    page = load_first_page()

    # getting the stories
    while page < 200:
        if page < 104:
            logger.error(f"{page=}, restarting browser...")
            restart_browser()
            break
        logging.debug(f"{page=}")
        print(f"{page}", end=".")
        text = try_get_text()
        if not text:
            time.sleep(0.1)
            continue
        if is_short_story_page(text):
            short_story_texts = split_short_stories_text(text)
            for short_story_text in short_story_texts:
                fresh_snapshot_obj.add_story(ShortStory(raw_text=short_story_text, page=page))
        else:
            fresh_snapshot_obj.add_story(Story(raw_text=text, page=page))

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


def load_first_page():
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
        page = poll_for_first_page_load(page, first_page_load_poll_tries)
    return page


def poll_for_first_page_load(page: int, polling_tries: int):
    if polling_tries % 1000 == 0:
        logger.error(f"{polling_tries=}. Restarting browser...")
        restart_browser()

    if polling_tries % 10 == 0:
        logger.warning(f"{polling_tries=}, {page=}, getting {START_FROM_PAGE}...")
        try:
            browser.get(f"https://nos.nl/teletekst#{START_FROM_PAGE}")
        except selenium.common.exceptions.WebDriverException as e:
            logger.error(f"Could not load page! {e}")
        time.sleep(1)
    page_loader = PageLoader(browser, page)
    page_loader.try_get_page()
    if page_loader.page >= 190:
        print(f"{page_loader.page=}")
        time.sleep(0.1)
    return page_loader.page


def try_get_text():
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
