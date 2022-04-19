import logging

import selenium

from constants import START_FROM_PAGE, SELECTOR_NEXT
from page_loader import PageLoader
from setup_logger import logger, log
import os
import datetime
import time
import requests
import json
import jellyfish
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
# todo: every archive size number of snapshots make a meta snapshot of the last archive to check old stories
#  then we can use the last archive(s) plus the pre-archive to make the merged dict to check against and we don't
#  have to keep extra dicts in the fresh folder.
# todo: make the merged dict based on time instead of count (e.g. all (meta-)dicts from within the last 48 hours)
# todo: if a minor change is made to a story, make an edit to the telegram, reddit(,etc) posts.
#  for reddit it might be preferable to edit over repost even if the change is major!
# todo: add reddit publisher bot
# todo: break up into classes/modules and make more object oriented

# todo: looks like the scraping is getting slower over time, the longer the program runs. Make the browser headless and
#  restart it every cycle or once every few cycles. Interestingly, if the browser window is brought to focus the
#  scraping seems to be fast again but immediately comes to a crawl when the window is in the background again.

# todo: remove and/or shorten the sleep times.

# todo: everything to the cloud (google?) (automatically pick up the code from github)

abort = False
publish_all = False
ROLLING_SNAPSHOTS_WINDOW_SIZE = 1000
SNAPSHOTS_ARCHIVE_SIZE = 1000
SELECTOR_CONTENT = "#teletekst > div.teletekst__content.js-tt-content > pre"
TELEGRAM_TEST_TTBOT_TOKEN = os.environ.get("TELEGRAM_TEST_TTBOT_TOKEN")
# https://api.telegram.org/bot[BOT_API_KEY]/[methodName]
TELEGRAM_API_URL = "https://api.telegram.org/bot{}/".format(TELEGRAM_TEST_TTBOT_TOKEN)
TELEGRAM_CHAT_ID = "@teletekst_test1"
LEVENSHTEIN_DISTANCE_THRESHOLD = 20


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
    global publish_all

    snapshots = os.listdir("snapshots")
    if len(snapshots) > (SNAPSHOTS_ARCHIVE_SIZE + ROLLING_SNAPSHOTS_WINDOW_SIZE):
        archive_old_snapshots(snapshots)

    previously_scraped_stories = get_merged_title_body_map()
    fresh_snapshot_obj = scrape_snapshot(browser)
    fresh_title_body_map = fresh_snapshot_obj.get_title_body_map()
    save_stories(fresh_title_body_map)
    log(f"{len(fresh_title_body_map)=}")
    if publish_all:
        for new_title, new_body in fresh_title_body_map.items():
            publish_story(new_title, new_body)
        publish_all = False
        return
    if fresh_title_body_map == previously_scraped_stories:
        log("No new stories: fresh_title_body_map == previously_scraped_stories")
    else:  # not identical
        if is_subset(fresh_title_body_map, previously_scraped_stories):
            log("No new stories: is_subset(fresh_title_body_map, previously_scraped_stories)")
        else:  # not subset
            for new_title, new_body in fresh_title_body_map.items():
                if new_title not in previously_scraped_stories:
                    for old_title, old_body in previously_scraped_stories.items():
                        if new_body == old_body:
                            log(f"{new_title} is a duplicate of {old_title}")
                            break
                        else:
                            ls_dist = jellyfish.levenshtein_distance(new_body, old_body)
                            if ls_dist < LEVENSHTEIN_DISTANCE_THRESHOLD:
                                log(f"{new_title} is a minor update from {old_title} ({ls_dist=})")
                                break
                    log(f"New story: {new_title}")
                    publish_story(new_title, new_body)
                else:  # new_title in previously_scraped_stories
                    old_body = previously_scraped_stories[new_title]
                    if new_body != old_body:
                        ls_dist = jellyfish.levenshtein_distance(new_body, old_body)
                        if ls_dist < LEVENSHTEIN_DISTANCE_THRESHOLD:
                            log(f"{new_title} got a minor update ({ls_dist=})")
                        else:
                            log(f"{new_title} got a major update ({ls_dist=})")
                            publish_story(new_title + " (update)",
                                          new_body + f"\n\n(Levenshtein distance: {ls_dist} operations)")


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
            unique_story_count = fresh_snapshot_obj.get_unique_story_count()
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
    if fresh_snapshot_obj.get_unique_story_count() < 1:
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


def is_subset(newly_scraped_stories: dict, previously_scraped_stories: dict):
    for new_title, new_story in newly_scraped_stories.items():
        if new_title not in previously_scraped_stories:
            return False
        else:
            old_story = previously_scraped_stories[new_title]
            if new_story != old_story:
                return False
    return True


def transform_to_normal_format(tt_format_text: str) -> str:
    def is_closing_quote(char, index, text):
        assert char == text[index] and char in ["'", '"']
        text_so_far = text[:index]
        if text_so_far.count(char) % 2 == 1:
            return True
        return False

    lines = tt_format_text.split("\n")
    for i, line in enumerate(lines):
        if line.strip() == "":
            lines[i] = "\n\n"
        else:
            lines[i] = line.strip() + " "
    compact_text = "".join(lines)
    new_text = compact_text
    correction_counter = 0
    for i, character in enumerate(compact_text):
        numbers = "0123456789"
        if i == 0:
            continue
        # ignore . in "..."
        if character == "." and compact_text[i + 1] == ".":
            continue
        # ignore . in big numbers
        if character == "." and (compact_text[i - 1] in numbers and
                                 compact_text[i + 1] in numbers and  # these do not go out of bounds because there is
                                 compact_text[i + 2] in numbers and  # an added space at the end and the rest does not
                                 compact_text[i + 3] in numbers):    # get evaluated
            continue
        # ignore , in decimal numbers
        elif character == "," and (compact_text[i - 1] in numbers and
                                   compact_text[i + 1] in numbers):
            continue
        # ignore . and ! and ? when followed by closing ' or "
        elif character in ".!?" and (compact_text[i + 1] in "'\"" and
                                     is_closing_quote(compact_text[i + 1], i + 1, compact_text)):
            continue
        elif character in ".,!?;:" and compact_text[i + 1].strip() != "":
            correction_counter += 1
            new_text = new_text[:i + correction_counter] + " " + compact_text[i + 1:]

    # remove the spaces at the end of the lines
    new_lines = new_text.splitlines()
    for i, line in enumerate(new_lines):
        if len(line) > 0 and line[-1] == " ":
            new_lines[i] = line.strip()
    new_text = "\n".join(new_lines)
    new_text = new_text.strip()
    return new_text


def publish_story(title: str, story: str):
    formatted_story = transform_to_normal_format(story)
    formatted_title = transform_to_normal_format(title)

    log(f"Publishing to telegram: {title}")
    publish_to_telegram(formatted_title, formatted_story)
    # publish_to_reddit(title, story)

    # publish_to_portfolio_website(title, story)

    # publish_to_twitter(title, story)
    # publish_to_facebook(title, story)
    # publish_to_instagram(title, story)
    # publish_to_linkedin(title, story)
    # publish_to_youtube(title, story)
    # publish_to_pinterest(title, story)
    # publish_to_tumblr(title, story)
    # publish_to_wordpress(title, story)
    # publish_to_medium(title, story)
    # publish_to_slack(title, story)
    # publish_to_discord(title, story)
    # publish_to_whatsapp(title, story)
    # publish_to_github_pages(title, story)
    # RSS???
    # Webhooks???


def publish_to_telegram(title: str, story: str):
    try:
        send_to_telegram_channel(f"<b><u>{title}</u></b>\n\n{story}")
    except requests.exceptions.SSLError as e:
        logger.error(f"Error while publishing to Telegram: {e}")


def send_to_telegram_channel(message: str):
    response = requests.get(TELEGRAM_API_URL + "sendMessage", params={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    })
    response.raise_for_status()


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
