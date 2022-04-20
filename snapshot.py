class Snapshot:
    def __init__(self):
        self.title_body_map = {}
        self.stories = []

    def add_story(self, story):
        self.stories.append(story)
        self.title_body_map[story.title] = story.body

    def get_title_body_map(self):
        return self.title_body_map

    def get_stories(self):
        return self.stories

    def get_unique_title_count(self):
        return len(self.title_body_map)
