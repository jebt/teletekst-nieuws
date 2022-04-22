from story import Story


class ShortStory(Story):
    def __init__(self, raw_text, page):
        super().__init__(raw_text, page)

    # title should be Kort nieuws binnenland or Kort nieuws buitenland
    # Same titles are fine. We insert the body as the key and the title as value. if title contains kort nieuws
