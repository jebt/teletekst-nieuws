import difflib

from setup_logger import log


def get_new_browser():
    use_chrome_for_docker = True
    if use_chrome_for_docker:
        browser_used = "chrome"
    else:
        browser_used = "firefox"
    log(f"Instantiating new headless {browser_used} browser...")
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.remote.remote_connection import LOGGER as SELENIUM_LOGGER
    from urllib3.connectionpool import log as urllib_logger
    from shutil import which
    from selenium import webdriver
    from logging import WARNING
    SELENIUM_LOGGER.setLevel(WARNING)
    urllib_logger.setLevel(WARNING)
    if use_chrome_for_docker:
        from webdriver_manager.chrome import ChromeDriverManager
        import chromedriver_binary  # Adds chromedriver binary to path
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("window-size=1024,768")
        chrome_options.add_argument("--no-sandbox")
        new_browser = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
    else:
        options = Options()
        options.headless = True
        options.binary = which("firefox")
        new_browser = webdriver.Firefox(options=options, service_log_path='./logs/geckodriver.log')
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


def split_short_stories_text(text: str) -> list[str]:
    closer = ""
    split = text.split("")
    short_story_texts = []
    for i in range(len(split) - 1):
        text = "".join([split[0], "", split[i + 1]]) + closer
        short_story_texts.append(text)
    return short_story_texts


def similarity_ratio(str1, str2):
    return difflib.SequenceMatcher(a=str1, b=str2).ratio()
