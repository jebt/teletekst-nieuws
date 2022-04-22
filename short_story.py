from story import Story


class ShortStory(Story):
    def __init__(self, raw_text, page):
        super().__init__(raw_text, page)

    # title should be Kort nieuws binnenland or Kort nieuws buitenland
    # the body is inserted as the key and the value in the dict if title contains kort nieuws
