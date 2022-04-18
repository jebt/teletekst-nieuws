class Story:
    def __init__(self, raw_text, page):
        self._raw_text = raw_text
        self.page = page
        self.title = self.extract_title()
        self.body = self.extract_body()

    def extract_title(self):
        title = self._raw_text.split(""
                                     )[1].strip().split("\n")[0].strip()
        return title

    def extract_body(self):
        lines = self._raw_text.split("")[1].split("")[0].split("\n")
        body = "\n".join([line.strip() for line in lines])[:-2]
        return body

    def __str__(self):
        return "<Story Object>" + self.title

    def __repr__(self):
        return "<Story Object>" + self.title
