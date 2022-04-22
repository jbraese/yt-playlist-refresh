from dataclasses import dataclass
import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple
import requests
from bs4 import BeautifulSoup
import yt_dlp


COLOR = "\033[0;36m"  # cyan
RESET_COLOR = "\033[00m"


class MyLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        # print(msg)
        pass


ydl_base_opts = {
    'logger': MyLogger(),
}


@dataclass
class YoutubeVideo:
    url: str
    title: str
    channel: str

    def display(self) -> str:
        text = ""
        if self.title:
            text += "Title: '" + self.title + "', "
        if self.channel:
            text += "Channel: '" + self.channel + "', "
        text += "URL: " + self.url
        return text


class NotArchivedOnWaybackError(Exception):
    pass


class NoTitleOnWaybackError(Exception):
    pass


def get_playlist_entries(url: str) -> List[YoutubeVideo]:
    ydl_opts = {
        'extract_flat': "in_playlist",  # just get video metadata
    }
    with yt_dlp.YoutubeDL(ydl_base_opts | ydl_opts) as ydlp:
        info = ydlp.extract_info(url)
        return [YoutubeVideo(entry["url"], entry["title"], entry["uploader"])
                for entry in info["entries"]]


def is_video_available(video: YoutubeVideo) -> Tuple[bool, YoutubeVideo]:
    ydl_opts = {
        "simulate": True,  # do not actually download anything
    }
    with yt_dlp.YoutubeDL(ydl_base_opts | ydl_opts) as ydlp:
        try:
            ydlp.download([video.url])
            return True, video
        except yt_dlp.utils.DownloadError as err:
            return False, video


def get_unavailable_videos(videos: List[YoutubeVideo]) -> List[YoutubeVideo]:
    unavailable_videos = []
    pool = ThreadPoolExecutor(max_workers=10)
    for available, video in pool.map(is_video_available, videos):
        if not available:
            unavailable_videos.append(video)
    return unavailable_videos


def get_youtube_search_results(query: str, number_results: int = 6) -> List[YoutubeVideo]:
    with yt_dlp.YoutubeDL(ydl_base_opts) as ydlp:
        results = ydlp.extract_info(
            f"ytsearch{str(number_results)}:{query}", download=False)['entries']
        return [YoutubeVideo(entry["webpage_url"], entry["title"], entry["channel"])
                for entry in results]


def suggest_alternatives(videos: List[YoutubeVideo]):
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(
            suggest_alternatives_for_one, video) for video in videos]
        print("Waiting for the next suggestions...", end="\r")
        for future in as_completed(futures):
            input("Press Enter to see suggestions for next unavailable video...\n\n")
            result = future.result()
            print(result, flush=True)
            print("Waiting for the next suggestions...", end="\r")
    print(" "*50)  # erase last waiting message


def suggest_alternatives_for_one(video: YoutubeVideo) -> str:
    result = "The following video was added to the playlist, but is no longer available: \n"
    result += COLOR + video.display() + RESET_COLOR + "\n"
    if video.title and video.channel:
        result += suggest_alternatives_from_title(video)
    else:
        result += suggest_alternatives_from_wayback(video)
    return result


def suggest_alternatives_from_title(video: YoutubeVideo) -> str:
    # if youtube still tells us information about the video, we use this to find replacement
    alternatives = get_youtube_search_results(video.title, 3)
    alternatives += get_youtube_search_results(video.title + video.channel, 3)
    result = "Based on video title and channel, maybe one of the following is a good substitute:\n"
    for idx, suggestion in enumerate(alternatives):
        result += " "*4 + str(idx+1) + ".: " + suggestion.display() + "\n"
    return result + "\n"


def suggest_alternatives_from_wayback(video: YoutubeVideo) -> str:
    # if we got no information about the video from youtube, we try the internet archive
    result = "Youtube doesn't tell us any metadata about the unavailable video. "
    try:
        archived_version = find_wayback_url(video)
        try:
            archived_title = get_video_title_from_wayback(archived_version)
            alternatives = get_youtube_search_results(archived_title, 6)
            result += "But based on a snapshot from the Internet Archive, we think the video was titled '"
            result += archived_title + \
                "'. (Archived link: " + archived_version + "). \n"
            result += "Consequently, maybe one of the following is a good substitute:\n"
            for idx, suggestion in enumerate(alternatives):
                result += " "*4 + str(idx+1) + ".: " + \
                    suggestion.display() + "\n"
        except NoTitleOnWaybackError as error:
            result += "While it seems to have been archived by the Internet Archive's Wayback Machine, "
            result += "we failed to automatically retreive the video title to suggest alternatives. "
            result += "You can try to find a working snapshot of the video under the following URL: "
            result += str(error)
    except NotArchivedOnWaybackError:
        result += "It also has not been archived by the Internet Archive's Wayback Machine. "
        result += "Consequently, we cannot suggest any alternatives for this video :("
    return result + "\n"


def find_wayback_url(video: YoutubeVideo) -> str:
    url = "https://archive.org/wayback/available?url=" + video.url
    response = requests.get(url)
    if response.status_code == 200 and 'application/json' in response.headers.get('Content-Type', ''):
        decoded = json.loads(response.content.decode('utf-8'))
        snapshot = decoded["archived_snapshots"]
        if snapshot == {}:
            raise NotArchivedOnWaybackError()
        else:
            return snapshot["closest"]["url"]


def get_video_title_from_wayback(url: str) -> str:
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        if hasattr(soup, "title") and soup.title is not None:
            title = clean_wayback_video_title(soup.title.string)
            if len(title) > 0:
                return title
        raise NoTitleOnWaybackError(url)


def clean_wayback_video_title(title: str) -> str:
    # heuristic based on looking at a few titles from the internet archive
    cleaned = title.strip().lower()
    cleaned = cleaned.removeprefix("youtube").removesuffix(
        "youtube").strip().removesuffix("-")
    return cleaned.strip()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='Find alternatives for unavailable videos in a youtube playlist.')
    parser.add_argument(
        "url", help="URL of a non-private playlist", type=str)
    args = parser.parse_args()
    url = args.url

    print("In order to refresh your playlist, we will try to find alternatives to its unavailable videos.", flush=True)

    playlist_entries = get_playlist_entries(url)
    print("Playlist contains {} videos, now checking which are available. This might take a second.".format(
        len(playlist_entries)))

    unavailable_videos = get_unavailable_videos(playlist_entries)
    print("\n Finished checking playlist, {} videos unavailable \n".format(
        len(unavailable_videos)), flush=True)

    suggest_alternatives(unavailable_videos)
