
def _is_closing_quote(char, index, text):
    """note that the single quote sign used as an apostrophe would be misinterpreted thus this function is imperfect"""
    assert char == text[index] and char in ["'", '"']
    text_so_far = text[:index]
    if text_so_far.count(char) % 2 == 1:
        return True
    return False


def transform_to_normal_format(tt_format_text: str) -> str:  # todo: refactor with regex and 3rd party libs?
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

        # ignore '.' in multiple dots like "..."
        if character == "." and compact_text[i + 1] == ".":
            continue

        # ignore '.' in big dot separated numbers e.g. "100.000"
        if character == "." and (compact_text[i - 1] in numbers and
                                 compact_text[i + 1] in numbers and  # these do not go out of bounds because there is
                                 compact_text[i + 2] in numbers and  # an added space at the end and the rest does not
                                 compact_text[i + 3] in numbers):    # get evaluated
            continue

        # ignore '.' in ".nl", ".com", ".net", ".org", ".eu", ".be" websites e.g. "reddit.com"
        if character == "." and (  # todo: replace by detection of lowercase letter after dot
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

        # ignore ',' in decimal numbers e.g. "0,75"
        elif character == "," and (compact_text[i - 1] in numbers and
                                   compact_text[i + 1] in numbers):
            continue

        # ignore '.', '!' and '?' when followed by closing "'" or '"' quotation mark e.g. "Hello!"
        elif character in ".!?" and (compact_text[i + 1] in "'\"" and
                                     _is_closing_quote(compact_text[i + 1], i + 1, compact_text)):
            continue

        # put in a space after .,!?;: if followed by something other than whitespace
        elif character in ".,!?;:" and compact_text[i + 1].strip() != "":
            correction_counter += 1
            new_text = new_text[:i + correction_counter] + " " + compact_text[i + 1:]

        # put in a space after closing " if it is followed by something other than whitespace
        elif character == '"' and _is_closing_quote('"', i, compact_text) and compact_text[i + 1].strip() != "" and \
                compact_text[i + 1] not in ".,!?;:":
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
