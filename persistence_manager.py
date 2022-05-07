import json
import os
import uuid as uuid_lib

from story import Story
from teletekst_nieuws_lib import similarity_ratio

SHORT_STORY_RATIO_THRESHOLD = 0.5
TITLE_RATIO_THRESHOLD = 0  # if body is identical
BODY_RATIO_THRESHOLD = 0.25  # if title is identical
TITLE_BODY_RATIO_THRESHOLD = 0.5  # if title and body are different


class PersistenceManager:
    def __init__(self, current_stories: list[Story] = None):
        self.current_stories = current_stories if current_stories else []
        self.persisted_stories = get_persisted_stories()

    def assign_uuids(self):
        for story in self.current_stories:
            for uuid, versions in self.persisted_stories.items():
                if story.title == versions["latest"]["title"] and story.body == versions["latest"]["body"]:
                    story.uuid = uuid
                    break

            if "kort nieuws" in story.title.lower():
                self.assign_short_story_uuid(story)
                continue

            self.assign_long_story_uuid(story)

    def assign_short_story_uuid(self, story: Story):
        best_match = None
        highest_ratio = 0
        for uuid, versions in self.persisted_stories.items():
            ratio = similarity_ratio(story.body, versions["latest"]["body"])
            if ratio > highest_ratio:
                highest_ratio = ratio
                best_match = uuid
        if highest_ratio >= SHORT_STORY_RATIO_THRESHOLD:
            story.uuid = best_match
        else:
            story.uuid = get_random_uuid()

    def assign_long_story_uuid(self, story: Story):
        best_body_match = None
        best_title_match = None
        best_title_body_match = None
        best_body_ratio = 0
        best_title_ratio = 0
        best_title_body_ratio = 0

        for uuid, versions in self.persisted_stories.items():
            persisted_title = versions["latest"]["title"]
            persisted_body = versions["latest"]["body"]

            body_ratio = similarity_ratio(story.body, persisted_body)
            title_ratio = similarity_ratio(story.title, persisted_title)
            title_body_ratio = similarity_ratio(story.title + story.body, persisted_title + persisted_body)

            if story.body == persisted_body:
                if title_ratio > best_title_ratio:
                    best_title_ratio = title_ratio
                    best_title_match = uuid
            elif story.title == persisted_title:
                if body_ratio > best_body_ratio:
                    best_body_ratio = body_ratio
                    best_body_match = uuid
            elif title_body_ratio > best_title_body_ratio:
                best_title_body_ratio = title_body_ratio
                best_title_body_match = uuid

        if best_title_ratio > TITLE_RATIO_THRESHOLD:
            story.uuid = best_title_match
            return
        elif best_body_ratio > BODY_RATIO_THRESHOLD:
            story.uuid = best_body_match
            return
        elif best_title_body_ratio > TITLE_BODY_RATIO_THRESHOLD:
            story.uuid = best_title_body_match
            return
        story.uuid = get_random_uuid()


def get_random_uuid():
    return str(uuid_lib.uuid4())


def get_persisted_stories() -> dict:
    if not os.path.isfile("persisted_stories.json"):
        with open("persisted_stories.json", "w") as f:
            json.dump({}, f)
    with open("persisted_stories.json", "r") as f:
        story_dict = json.load(f)
    return story_dict
