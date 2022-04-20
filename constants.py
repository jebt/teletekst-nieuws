from os import environ

# css selectors
SELECTOR_PAGE = "span.yellow:nth-child(2) > a:nth-child(1)"
START_FROM_PAGE = 104  # 104-190
SELECTOR_NEXT = ".next"

# telegram config
TELEGRAM_TEST_TTBOT_TOKEN = environ.get("TELEGRAM_TEST_TTBOT_TOKEN")
TELEGRAM_API_URL = "https://api.telegram.org/bot{}/".format(TELEGRAM_TEST_TTBOT_TOKEN)
TELEGRAM_CHAT_ID = "@teletekst_test1"

LEVENSHTEIN_DISTANCE_THRESHOLD = 20
