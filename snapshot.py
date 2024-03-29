class Snapshot:
    def __init__(self):
        self.title_body_map = {}
        self.stories = []

    def add_story(self, story):
        if (story.title not in self.title_body_map) and (story.body not in self.title_body_map):  # prevent duplicates
            self.stories.append(story)
        if "kort nieuws" in story.title.lower():
            self.title_body_map[story.body] = story.body
        else:
            self.title_body_map[story.title] = story.body

    def get_title_body_map(self):
        return self.title_body_map

    def get_stories(self):
        return self.stories

    def get_unique_title_count(self):
        return len(self.title_body_map)
