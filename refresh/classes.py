from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


COLOR = "\033[0;36m"  # cyan
RESET_COLOR = "\033[00m"


@dataclass
class YoutubeVideo:
    """Describes a Youtube video that is available or unavailable"""

    url: str
    title: str
    channel: str

    def print_video_info(self):
        info = ""
        if self.title:
            info += "Title: '" + self.title + "', "
        if self.channel:
            info += "Channel: '" + self.channel + "', "
        info += "URL: " + self.url
        print(info)


class RefreshSource(ABC):
    """Abstract class describing where alternatives for an unavailable video were inferred from."""

    @abstractmethod
    def print_source_info(self):
        pass


@dataclass
class RefreshSourceAPI(RefreshSource):
    """Alternatives for an unavailable video were inferred from its Youtube title and channel name."""

    def print_source_info(self):
        print("For this video, title and channel are still available from Youtube.")


@dataclass
class RefreshSourceWayback(RefreshSource):
    """Alternatives for an unavailable video were inferred from a snapshot on the Internet Archive's Wayback Machine."""

    wayback_url: str
    archived_date: str
    video_title: str

    def print_source_info(self):
        info = "Youtube doesn't tell us any metadata about the unavailable video. "
        info += "But based on a snapshot from the Internet Archive, we think the video was titled"
        info += " '" + self.video_title + "'. "
        info += "You can find an archived version from " + \
            self.archived_date + " at " + self.wayback_url + "."
        print(info)


@dataclass
class RefreshResult(ABC):
    """Abstract class describing results of search for alternatives of one unavailable video"""

    video_to_refresh: YoutubeVideo

    @abstractmethod
    def print_result(self):
        pass

    def print_intro(self):
        print("\n\nThe following video was added to the playlist, but is no longer available:")
        print(COLOR, end="")
        self.video_to_refresh.print_video_info()
        print(RESET_COLOR, end="")




@dataclass
class RefreshSuccess(RefreshResult):
    """Describing inferred alternatives and their source for one unavailable Youtube video"""

    alternatives: List[YoutubeVideo]
    source: RefreshSource

    def print_result(self):
        self.print_intro()
        self.source.print_source_info()
        print("\nConsequently, maybe one of the following is a good substitute:")
        for idx, alternative in enumerate(self.alternatives):
            print(str(idx + 1) + ".: ", end="")
            alternative.print_video_info()


@dataclass
class RefreshFailure(RefreshResult, ABC):
    """Abstract class showing that no alternatives were found for one unavailable video"""

    @abstractmethod
    def print_result(self):
        pass


@dataclass
class NotArchivedFailure(RefreshFailure):
    """No alternatives were found for the unavailable video because it was not archived by Wayback Machine"""

    def print_result(self):
        self.print_intro()
        result = "Youtube doesn't tell us any metadata about the unavailable video. "
        result += "It also has not been archived by the Internet Archive's Wayback Machine. "
        result += "Consequently, we cannot suggest any alternatives for this video :("
        print(result)


@dataclass
class NoTitleInArchiveFailure(RefreshFailure):
    """No alternatives were found for the unavailable video because its title couldnt be extracted from Wayback Machine"""

    wayback_url: str

    def print_result(self):
        self.print_intro()
        result = "Youtube doesn't tell us any metadata about the unavailable video. "
        result += "While it seems like it has been archived by the Internet Archive's Wayback Machine, "
        result += "we failed to automatically retreive the video title and cannot suggest alternatives. "
        result += "Maybe you can still find some information under the following URL: "
        result += self.wayback_url + "."
        print(result)
