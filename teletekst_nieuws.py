import logging
import sys
import os
import datetime
import time
import requests
import json

from selenium import webdriver
from selenium.webdriver.common.by import By

SELECTOR_NEXT = "#teletekst > aside > nav.teletekst__pager.js-tt-pager > a.next.js-tt-next"
SELECTOR_CONTENT = "#teletekst > div.teletekst__content.js-tt-content > pre"
SELECTOR_PAGE = "span.yellow:nth-child(2) > a:nth-child(1)"
START_FROM_PAGE = 104  # 104-190
QUICK_TEST = False
TELEGRAM_TEST_TTBOT_TOKEN = os.environ.get("TELEGRAM_TEST_TTBOT_TOKEN")
# https://api.telegram.org/bot[BOT_API_KEY]/[methodName]
TELEGRAM_API_URL = "https://api.telegram.org/bot{}/".format(TELEGRAM_TEST_TTBOT_TOKEN)
TELEGRAM_CHAT_ID = "@teletekst_test1"
CYCLE_SLEEP_SECONDS = 60


def send_to_telegram_channel(message: str):
    response = requests.get(TELEGRAM_API_URL + "sendMessage", params={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        })
    response.raise_for_status()


def main():
    set_up_logging()
    log("\n########## START ##########\n")

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
    root_logger.setLevel(logging.DEBUG)

    if not os.path.exists("logs"):
        os.makedirs("logs")
    log_file_name = f"logs/{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

    file_handler = logging.FileHandler(log_file_name)
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)


def log(message):
    logging.info(message)


def bot_cycle(browser):
    if QUICK_TEST:
        previously_scraped_stories = load_stories_by_sorted_files_index(-2)
        newly_scraped_stories = load_stories_by_sorted_files_index(-1)  # latest saved
    else:
        previously_scraped_stories = load_stories_by_sorted_files_index(-1)
        newly_scraped_stories = scrape_stories(browser)
        save_stories(newly_scraped_stories)
    if newly_scraped_stories == previously_scraped_stories:
        log("No new stories")
    else:
        for title, story in newly_scraped_stories.items():
            if title not in previously_scraped_stories:
                log(f"New story: {title}")
                publish_story(title, story)
            else:
                if previously_scraped_stories[title] != story:
                    log(f"Updated story: {title}")
                    logging.debug(f"old story:\n{previously_scraped_stories[title]}")
                    logging.debug(f"new story:\n{story}")


def transform_to_normal_format(tt_format_text: str) -> str:  # todo: write tests for this function
    lines = tt_format_text.split("\n")
    for i, line in enumerate(lines):
        if line.strip() == "":
            lines[i] = "\n\n"
        else:
            lines[i] = line.strip() + " "
    compact_text, new_text = "".join(lines)
    correction_counter = 0
    for i, character in enumerate(compact_text):
        if character in ".,!?;:" and compact_text[i + 1].strip() != "":
            correction_counter += 1
            new_text = new_text[:i + correction_counter] + " " + compact_text[i:]
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
    send_to_telegram_channel(f"*{title}*\n{story}")


def load_stories_by_sorted_files_index(index: int) -> dict:
    files = os.listdir("data")
    files.sort()
    file = files[index]
    with open(f"data/{file}", "r") as f:
        saved_stories = json.load(f)
    log(f"Loaded {len(saved_stories)} stories from {file}")
    return saved_stories


def scrape_stories(browser) -> dict:
    browser.get(f"https://nos.nl/teletekst#{START_FROM_PAGE}")
    time.sleep(15)
    next_button = browser.find_element(by=By.CSS_SELECTOR, value=SELECTOR_NEXT)
    next_page = int(next_button.get_attribute("href").split("#")[1])
    all_stories_dict = {}
    while next_page <= 200:
        page = int(browser.find_element(by=By.CSS_SELECTOR, value=SELECTOR_PAGE).text)
        logging.debug(f"{page=}")
        text = browser.find_element(by=By.CSS_SELECTOR, value=SELECTOR_CONTENT).text
        title = text.split(""
                           )[1].strip().split("\n")[0].strip()
        lines = text.split("")[1].split("")[0].split("\n")
        story = "\n".join([line.strip() for line in lines])[:-2]
        all_stories_dict[title] = story
        if next_page >= 200:
            break
        next_button.click()
        time.sleep(5)
        next_page = int(next_button.get_attribute("href").split("#")[1])
    return all_stories_dict


def save_stories(stories: dict):
    time_string = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs("data", exist_ok=True)
    with open(f"data/{time_string}", "w") as f:
        json.dump(stories, f, indent=4)


if __name__ == "__main__":
    main()
