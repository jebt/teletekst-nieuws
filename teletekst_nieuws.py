import logging
import sys
import os
import datetime
import time
import requests
import json
import jellyfish

from story import Story
from logging.handlers import TimedRotatingFileHandler
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from shutil import which, move


# todo: handle multiple "kort nieuws binnenland/buitenland" stories. (list in dict?)
# todo: handle number formatting (no added space) (*N.NNN* and *N,N*)
# todo: if a minor change is made to a story, make an edit to the telegram, reddit(,etc) posts.
#  for reddit it might be preferable to edit over repost even if the change is major!
# todo: add reddit publisher bot
# todo: break up into classes

# todo: looks like the scraping is getting slower over time, the longer the program runs. Make the browser headless and
#  restart it every cycle or once every few cycles. Interestingly, if the browser window is brought to focus the
#  scraping seems to be fast again but immediately comes to a crawl when the window is in the background again.

# todo: remove and/or shorten the sleep times.

# todo: everything to the cloud (google?) (automatically pick up the code from github)

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
# CYCLE_SLEEP_SECONDS = 5
LEVENSHTEIN_DISTANCE_THRESHOLD = 20


def main():
    set_up_logging()
    log("########## START ##########\n")

    options = Options()
    options.headless = True
    options.binary = which("firefox")
    browser = webdriver.Firefox(options=options)
    cycle_counter = 0
    while True:
        cycle_counter += 1
        log(f"Cycle {cycle_counter}...")
        bot_cycle(browser)
        # log(f"Sleeping for {CYCLE_SLEEP_SECONDS} seconds...")
        # time.sleep(CYCLE_SLEEP_SECONDS)

    # log("########## END ##########\n")


def set_up_logging():
    log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    os.makedirs("logs", exist_ok=True)
    # log_file_name = f"logs/{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    log_file_name = f"logs/teletekst_nieuws.log"

    # timed rotated log files
    file_handler = logging.handlers.TimedRotatingFileHandler(log_file_name, when="midnight", interval=1)
    file_handler.suffix = "%Y%m%d"
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)


def log(message):
    logging.info(message)


def bot_cycle(browser):  # todo: tests and make flow more readable (extract functions, add comments)
    snapshots = os.listdir("snapshots")
    if len(snapshots) > (SNAPSHOTS_ARCHIVE_SIZE + ROLLING_SNAPSHOTS_WINDOW_SIZE):
        archive_old_snapshots(snapshots)

    previously_scraped_stories = get_merged_snapshots()
    fresh_snapshot = scrape_snapshot(browser)
    save_stories(fresh_snapshot)
    log(f"{len(fresh_snapshot)=}")
    if fresh_snapshot == previously_scraped_stories:
        log("No new stories: fresh_snapshot == previously_scraped_stories")
    else:  # not identical
        if is_subset(fresh_snapshot, previously_scraped_stories):
            log("No new stories: is_subset(fresh_snapshot, previously_scraped_stories)")
        for new_title, new_body in fresh_snapshot.items():
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
                        publish_story(new_title + " (update)", new_body)


def archive_old_snapshots(snapshots: list[str]):
    snapshots.sort()
    time_string = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs(f"snapshots_archive/{time_string}", exist_ok=True)
    for file in snapshots[:SNAPSHOTS_ARCHIVE_SIZE]:
        # move file to new directory
        move(f"snapshots/{file}", f"snapshots_archive/{time_string}/{file}")


def scrape_snapshot(browser) -> dict:  # todo: refactor
    log("Scraping stories...")
    page = 190
    browser.get(f"https://nos.nl/teletekst#{START_FROM_PAGE}")
    time.sleep(0.5)
    tries = 0
    while page == 190:
        tries += 1
        if tries % 10 == 0:
            logging.warning(f"{tries=}, {page=}")
            browser.get(f"https://nos.nl/teletekst#{START_FROM_PAGE}")
            time.sleep(0.5)
        try:
            page = int(browser.find_element(by=By.CSS_SELECTOR, value=SELECTOR_PAGE).text)
        except NoSuchElementException:
            log("NoSuchElementException")
        except StaleElementReferenceException:
            log("StaleElementReferenceException")
        if page == 190:
            print("Page is 190")
            time.sleep(0.1)
    all_stories_dict = {}
    new_stories = []
    while page < 200:
        logging.debug(f"{page=}")
        print(f"{page}", end=".")
        dots = 1
        try:
            text = browser.find_element(by=By.CSS_SELECTOR, value=SELECTOR_CONTENT).text
        except StaleElementReferenceException:
            log("StaleElementReferenceException")
            time.sleep(0.1)
            continue
        story = Story(raw_text=text, page=page)
        all_stories_dict[story.title] = story.body
        new_stories.append(story)

        next_button = browser.find_element(by=By.CSS_SELECTOR, value=SELECTOR_NEXT)
        next_page = int(next_button.get_attribute("href").split("#")[1])
        if next_page >= 200:
            print("done")
            log(f"{next_page=}, breaking out of next page looping...")
            story_count = len(all_stories_dict)
            if story_count <= 1:
                logging.error(f"{next_page=} while {story_count=}!")
            break
        next_button.click()
        time.sleep(0.1)
        prev_page = page
        while page == prev_page:
            try:
                page = int(browser.find_element(by=By.CSS_SELECTOR, value=SELECTOR_PAGE).text)
            except StaleElementReferenceException:
                # log("StaleElementReferenceException")
                pass
            if page == prev_page:
                print(".", end="")
                dots += 1
                if dots % 20 == 0:
                    logging.warning(f"{dots=}, {page=}")
                    next_button = browser.find_element(by=By.CSS_SELECTOR, value=SELECTOR_NEXT)
                    next_button.click()
                time.sleep(0.1)
    if len(all_stories_dict) < 1:
        logging.error("No stories found!")
    return all_stories_dict


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


def get_merged_snapshots() -> dict:
    snapshots = load_list_of_last_story_snapshots(ROLLING_SNAPSHOTS_WINDOW_SIZE)
    merged_snapshots = {}
    for snapshot in snapshots:
        merged_snapshots.update(snapshot)
    return merged_snapshots


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
