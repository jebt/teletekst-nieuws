import logging
import sys
import os
import datetime
import time
import requests
import json
import jellyfish
import snapshot

from story import Story
from logging.handlers import TimedRotatingFileHandler
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.remote_connection import LOGGER as SELENIUM_LOGGER
from urllib3.connectionpool import log as urllib_logger
from shutil import which, move


# todo: handle multiple "kort nieuws binnenland/buitenland" stories. (list in dict?)
# todo: handle number formatting (no added space) (*N.NNN* and *N,N*)
# todo: every archive size number of snapshots make a meta snapshot of the last archive to check old stories
# todo: if a minor change is made to a story, make an edit to the telegram, reddit(,etc) posts.
#  for reddit it might be preferable to edit over repost even if the change is major!
# todo: add reddit publisher bot
# todo: break up into classes

# todo: looks like the scraping is getting slower over time, the longer the program runs. Make the browser headless and
#  restart it every cycle or once every few cycles. Interestingly, if the browser window is brought to focus the
#  scraping seems to be fast again but immediately comes to a crawl when the window is in the background again.

# todo: remove and/or shorten the sleep times.

# todo: everything to the cloud (google?) (automatically pick up the code from github)

publish_all = False
ROLLING_SNAPSHOTS_WINDOW_SIZE = 1000
SNAPSHOTS_ARCHIVE_SIZE = 1000
SELECTOR_NEXT = ".next"
SELECTOR_CONTENT = "#teletekst > div.teletekst__content.js-tt-content > pre"
SELECTOR_PAGE = "span.yellow:nth-child(2) > a:nth-child(1)"
START_FROM_PAGE = 104  # 104-190
TELEGRAM_TEST_TTBOT_TOKEN = os.environ.get("TELEGRAM_TEST_TTBOT_TOKEN")
# https://api.telegram.org/bot[BOT_API_KEY]/[methodName]
TELEGRAM_API_URL = "https://api.telegram.org/bot{}/".format(TELEGRAM_TEST_TTBOT_TOKEN)
TELEGRAM_CHAT_ID = "@teletekst_test1"
LEVENSHTEIN_DISTANCE_THRESHOLD = 20


def main():
    set_up_logging()
    log("########## START ##########\n")

    options = Options()
    options.headless = True
    options.binary = which("firefox")
    SELENIUM_LOGGER.setLevel(logging.WARNING)
    urllib_logger.setLevel(logging.WARNING)
    options.log.level = "warn"
    browser = webdriver.Firefox(options=options)
    cycle_counter = 0
    while True:
        cycle_counter += 1
        log(f"Cycle {cycle_counter}...")
        bot_cycle(browser)

    # log("########## END ##########\n")


def set_up_logging():
    log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    os.makedirs("logs", exist_ok=True)
    # log_file_name = f"logs/{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    log_file_name = f"logs/teletekst_nieuws.log"

    # timed rotated log files
    file_handler = logging.handlers.TimedRotatingFileHandler(log_file_name, when="midnight", interval=1)
    file_handler.suffix = "%Y%m%d"
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)


def log(message):
    logging.info(message)


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
                            publish_story(new_title + " (update)", new_body + f"\n\n{ls_dist=}")


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
        dots = 1
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
        prev_page = page
        while page == prev_page:
            page = load_next_page(browser, dots, page, prev_page)

    # finalizing the scraping process
    if fresh_snapshot_obj.get_unique_story_count() < 1:
        logging.error("No stories found!")
    return fresh_snapshot_obj


def load_first_page(browser):
    log("Scraping stories...")
    page = 190
    browser.get(f"https://nos.nl/teletekst#{START_FROM_PAGE}")
    time.sleep(0.5)
    tries = 0
    while page >= 190:
        page = poll_for_first_page_load(browser, page, tries)
    return page


def load_next_page(browser, dots, page, prev_page):
    page = try_get_page(browser, page)
    if page == prev_page:
        print(".", end="")
        dots += 1
        if dots % 200 == 0:
            logging.error(f"{dots=}, {page=}")
            log(f"Reloading the first story page... ({START_FROM_PAGE=})")
            browser.get(f"https://nos.nl/teletekst#{START_FROM_PAGE}")
            time.sleep(0.5)
            dots = 0
        if dots % 20 == 0:
            logging.warning(f"{dots=}, {page=}")
            try_click_next(browser, page)
        time.sleep(0.1)
    return page


def try_click_next(browser, page):
    try:
        next_button = browser.find_element(by=By.CSS_SELECTOR, value=SELECTOR_NEXT)
        next_button.click()
    except NoSuchElementException:
        logging.error("NoSuchElementException")
        log(f"Reloading the page... ({page=})")
        browser.get(f"https://nos.nl/teletekst#{page}")
        time.sleep(0.5)


def poll_for_first_page_load(browser, page, tries):
    tries += 1
    if tries % 10 == 0:
        logging.warning(f"{tries=}, {page=}")
        browser.get(f"https://nos.nl/teletekst#{START_FROM_PAGE}")
        time.sleep(0.5)
    page = try_get_page(browser, page)
    if page >= 190:
        print(f"{page=}")
        time.sleep(0.1)
    return page


def try_get_text(browser):
    text = None
    try:
        text = browser.find_element(by=By.CSS_SELECTOR, value=SELECTOR_CONTENT).text
    except StaleElementReferenceException:
        log("StaleElementReferenceException")
    return text


def try_get_page(browser, page):
    try:
        elem = browser.find_element(by=By.CSS_SELECTOR, value=SELECTOR_PAGE)
        page = int(elem.text)
    except StaleElementReferenceException:
        print("E", end="\n")
        logging.debug("StaleElementReferenceException")
    except NoSuchElementException:
        print("E", end="\n")
        logging.info("NoSuchElementException")
    return page


def is_subset(newly_scraped_stories: dict, previously_scraped_stories: dict):
    for new_title, new_story in newly_scraped_stories.items():
        if new_title not in previously_scraped_stories:
            return False
        else:
            old_story = previously_scraped_stories[new_title]
            if new_story != old_story:
                return False
    return True


def transform_to_normal_format(tt_format_text: str) -> str:  # todo: write tests for this function
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
        if character in ".,!?;:" and compact_text[i + 1].strip() != "":
            correction_counter += 1
            new_text = new_text[:i + correction_counter] + " " + compact_text[i+1:]
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
    send_to_telegram_channel(f"<b><u>{title}</u></b>\n\n{story}")


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
