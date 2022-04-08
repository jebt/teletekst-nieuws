import logging
import sys
import os
import datetime
import time
import requests
import json
import jellyfish

from selenium import webdriver
from selenium.webdriver.common.by import By

# todo: handle multiple "kort nieuws binnenland/buitenland" stories. (list in dict?)
# todo: handle number formatting (no added space) (*N.NNN* and *N,N*)
# todo: rename data to snapshots (folder and uses in paths)
# todo: auto archive (or delete) old snapshots and logs
# todo: remove QUICK_TEST and use it for testing only?


SELECTOR_NEXT = ".next"
SELECTOR_CONTENT = "#teletekst > div.teletekst__content.js-tt-content > pre"
SELECTOR_PAGE = "span.yellow:nth-child(2) > a:nth-child(1)"
START_FROM_PAGE = 104  # 104-190
QUICK_TEST = False
TELEGRAM_TEST_TTBOT_TOKEN = os.environ.get("TELEGRAM_TEST_TTBOT_TOKEN")
# https://api.telegram.org/bot[BOT_API_KEY]/[methodName]
TELEGRAM_API_URL = "https://api.telegram.org/bot{}/".format(TELEGRAM_TEST_TTBOT_TOKEN)
TELEGRAM_CHAT_ID = "@teletekst_test1"
CYCLE_SLEEP_SECONDS = 5


def main():
    set_up_logging()
    log("########## START ##########\n")

    browser = webdriver.Firefox()
    cycle_counter = 0
    while True:
        cycle_counter += 1
        log(f"Cycle {cycle_counter}...")
        bot_cycle(browser)
        log(f"Sleeping for {CYCLE_SLEEP_SECONDS} seconds...")
        time.sleep(CYCLE_SLEEP_SECONDS)


def set_up_logging():
    log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    os.makedirs("logs", exist_ok=True)
    log_file_name = f"logs/{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

    file_handler = logging.FileHandler(log_file_name)
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)


def log(message):
    logging.info(message)


def bot_cycle(browser):  # todo: tests and make flow more readable (extract functions, add comments)
    if QUICK_TEST:
        previously_scraped_stories = load_snapshot_by_sorted_files_index(-2)
        newly_scraped_stories = load_snapshot_by_sorted_files_index(-1)  # latest saved
    else:
        previously_scraped_stories = get_merged_snapshots()
        newly_scraped_stories = scrape_stories(browser)
        save_stories(newly_scraped_stories)
        log(f"{len(newly_scraped_stories)=}")
    if newly_scraped_stories == previously_scraped_stories:
        log("No new stories")
        logging.info("newly_scraped_stories == previously_scraped_stories")
    else:
        if is_subset(newly_scraped_stories, previously_scraped_stories):
            log("No new stories")
            logging.info("is_subset(newly_scraped_stories, previously_scraped_stories)")
        for new_title, new_story in newly_scraped_stories.items():
            if new_title not in previously_scraped_stories:
                for old_title, old_story in previously_scraped_stories.items():
                    # todo: I believe there's 2 more cases to be caught:
                    #  - and title small change & story small change (ignore)
                    #  - title small change & story big change (post as update)
                    # ls_dist_title = jellyfish.levenshtein_distance(new_title, old_title)
                    # if ls_dist_title < 4:
                    #   check the distance between the 2 stories, ignore if small, post as update if big
                    if new_story == old_story:
                        log(f"{new_title} is a duplicate of {old_title}")
                        break
                    else:
                        ls_dist = jellyfish.levenshtein_distance(new_story, old_story)
                        if ls_dist < 10:
                            log(f"{new_title} is a small update from {old_title} ({ls_dist=})")
                            break
                log(f"New story: {new_title}")
                publish_story(new_title, new_story)
            else:  # new_title in previously_scraped_stories
                old_story = previously_scraped_stories[new_title]
                if new_story != old_story:
                    ls_dist = jellyfish.levenshtein_distance(new_story, old_story)
                    if ls_dist < 10:
                        log(f"{new_title} got a small update ({ls_dist=})")
                    else:
                        log(f"{new_title} got a significant update ({ls_dist=})")
                        publish_story(new_title + " (update)", new_story)


def is_subset(newly_scraped_stories: dict, previously_scraped_stories: dict):
    for new_title, new_story in newly_scraped_stories.items():
        if new_title not in previously_scraped_stories:
            return False
        else:
            old_story = previously_scraped_stories[new_title]
            if new_story != old_story:
                return False
    return True


def scrape_stories(browser) -> dict:
    print("Scraping stories", end="...")
    browser.get(f"https://nos.nl/teletekst#{START_FROM_PAGE}")
    time.sleep(15)
    page = int(browser.find_element(by=By.CSS_SELECTOR, value=SELECTOR_PAGE).text)
    all_stories_dict = {}
    while page < 200:
        logging.debug(f"{page=}")
        print(f"{page}", end="...")
        text = browser.find_element(by=By.CSS_SELECTOR, value=SELECTOR_CONTENT).text
        title = text.split(""
                           )[1].strip().split("\n")[0].strip()
        lines = text.split("")[1].split("")[0].split("\n")
        story = "\n".join([line.strip() for line in lines])[:-2]
        all_stories_dict[title] = story
        next_button = browser.find_element(by=By.CSS_SELECTOR, value=SELECTOR_NEXT)
        next_page = int(next_button.get_attribute("href").split("#")[1])
        if next_page >= 200:
            print("done")
            log(f"{next_page=}, breaking next page looping...")
            story_count = len(all_stories_dict)
            if story_count <= 1:
                logging.error(f"{next_page=} while {story_count=}!")
            break
        next_button.click()
        time.sleep(5)
        page = int(browser.find_element(by=By.CSS_SELECTOR, value=SELECTOR_PAGE).text)
    return all_stories_dict


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

    # publish_to_twitter(title, story)
    # publish_to_facebook(title, story)
    # publish_to_instagram(title, story)
    # publish_to_linkedin(title, story)
    # publish_to_reddit(title, story)
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
    files = os.listdir("data")
    files.sort()
    file = files[index]
    with open(f"data/{file}", "r") as f:
        saved_stories = json.load(f)
    log(f"Loaded {len(saved_stories)} stories from {file}")
    return saved_stories


def get_merged_snapshots() -> dict:
    snapshots = load_list_of_last_story_snapshots(10)
    merged_snapshots = {}
    for snapshot in snapshots:
        merged_snapshots.update(snapshot)
    return merged_snapshots


def load_list_of_last_story_snapshots(how_many_if_available: int) -> list:
    files = os.listdir("data")
    files.sort()
    if len(files) > how_many_if_available:
        files = files[-how_many_if_available:]
    snapshots = []
    for file in files:
        with open(f"data/{file}", "r") as f:
            snapshots.append(json.load(f))
    log(f"Loaded last {len(snapshots)} snapshots")
    return snapshots


def save_stories(stories: dict):
    time_string = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs("data", exist_ok=True)
    with open(f"data/{time_string}.json", "w") as f:
        json.dump(stories, f, indent=4)


if __name__ == "__main__":
    main()
