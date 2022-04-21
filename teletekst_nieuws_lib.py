from setup_logger import log


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
        # ignore . in .nl, .com, .net, .org, .eu, .be
        if character == "." and (
                (compact_text[i + 1] == 'n' and
                 compact_text[i + 2] == 'l') or
                (compact_text[i + 1] == 'c' and
                 compact_text[i + 2] == 'o' and
                 compact_text[i + 3] == 'm') or
                (compact_text[i + 1] == 'n' and
                 compact_text[i + 2] == 'e' and
                 compact_text[i + 3] == 't') or
                (compact_text[i + 1] == 'o' and
                 compact_text[i + 2] == 'r' and
                 compact_text[i + 3] == 'g') or
                (compact_text[i + 1] == 'e' and
                 compact_text[i + 2] == 'u') or
                (compact_text[i + 1] == 'b' and
                 compact_text[i + 2] == 'e')):
            continue

        # ignore , in decimal numbers
        elif character == "," and (compact_text[i - 1] in numbers and
                                   compact_text[i + 1] in numbers):
            continue

        # ignore . and ! and ? when followed by closing ' or "
        elif character in ".!?" and (compact_text[i + 1] in "'\"" and
                                     is_closing_quote(compact_text[i + 1], i + 1, compact_text)):
            continue

        # put in a space after .,!?;: if followed by something other than whitespace
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
