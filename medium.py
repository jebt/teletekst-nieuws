from abc import ABC, abstractmethod

from story import Story


class Medium(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def notify(self, story: Story): ...
