import jellyfish

from constants import LEVENSHTEIN_DISTANCE_THRESHOLD
from setup_logger import log
from snapshot import Snapshot
from story import Story
from telegram import Telegram
from teletekst_nieuws_lib import is_subset

scopes = ["everything",
          "new",
          "current_major_updates",
          "current_minor_updates",
          "all_current_updates",
          "current",
          "old",
          "new_and_major_updates",
          "new_and_all_updates", ]


class Publisher:
    def __init__(self, previously_scraped_stories: dict, fresh_snapshot_obj: Snapshot):
        self.previously_scraped_stories = previously_scraped_stories
        self.fresh_snapshot_obj = fresh_snapshot_obj

        telegram = Telegram()
        reddit = None  # todo: implement
        # portfolio_website, twitter, facebook, instagram, linkedin, youtube, pinterest, tumblr, wordpress, medium, \
        #     slack, discord, whatsapp, github_pages, rss, webhooks = \
        #     None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None

        self.media = [telegram, reddit]

    def register_medium(self, medium):
        self.media.append(medium)

    def unregister_medium(self, medium):
        self.media.remove(medium)

    def publish(self, scope="new_and_major_updates"):
        if scope not in scopes:
            raise Exception("Invalid scope")
        else:
            if scope == "current":
                self.publish_current()
            elif scope == "new_and_major_updates":
                self.publish_new_and_major_updates()
            else:
                raise Exception("Scope not implemented")

    def publish_current(self):
        for story in self.fresh_snapshot_obj.stories:
            self.dispatch_new(story)

    def dispatch_new(self, story: Story):
        for medium in self.media:
            if medium is None:
                continue
            medium.notify(story)

    def dispatch_update(self, story: Story, ls_dist: int):
        story.formatted_title = story.formatted_title + " (update)"
        story.formatted_body = story.formatted_body + f"\n\n(Levenshtein distance: {ls_dist} operations)"
        for medium in self.media:
            if medium is None:
                continue
            medium.notify(story)

    def publish_new_and_major_updates(self):
        fresh_title_body_map = self.fresh_snapshot_obj.get_title_body_map()
        previously_scraped_stories = self.previously_scraped_stories
        if fresh_title_body_map == previously_scraped_stories:
            log("No new stories: fresh_title_body_map == previously_scraped_stories")
        else:  # not identical
            if is_subset(fresh_title_body_map, previously_scraped_stories):
                log("No new stories: is_subset(fresh_title_body_map, previously_scraped_stories)")
            else:  # not subset
                for story in self.fresh_snapshot_obj.get_stories():
                    new_title = story.title
                    new_body = story.body
                    if "kort nieuws" in new_title.lower():
                        if new_body in previously_scraped_stories:
                            continue
                    duplicate = False
                    minor_update = False
                    if new_title not in previously_scraped_stories:
                        for old_title, old_body in previously_scraped_stories.items():
                            if new_body == old_body:
                                log(f"{new_title} is a duplicate of {old_title}")
                                duplicate = True
                                break
                            else:  # not a duplicate
                                ls_dist = jellyfish.levenshtein_distance(new_body, old_body)
                                if ls_dist < LEVENSHTEIN_DISTANCE_THRESHOLD:
                                    log(f"{new_title} is a minor update from {old_title} ({ls_dist=})")
                                    minor_update = True
                                    break
                                else:  # not a minor update
                                    pass  # todo: should we implement a way to detect a major update on a short story?
                        if not duplicate and not minor_update:
                            log(f"New story: {new_title}")
                            self.dispatch_new(story)
                    else:  # new_title in previously_scraped_stories
                        old_body = previously_scraped_stories[new_title]
                        if new_body != old_body:
                            ls_dist = jellyfish.levenshtein_distance(new_body, old_body)
                            if ls_dist < LEVENSHTEIN_DISTANCE_THRESHOLD:
                                log(f"{new_title} got a minor update ({ls_dist=})")
                            else:
                                log(f"{new_title} got a major update ({ls_dist=})")
                                self.dispatch_update(story, ls_dist)
