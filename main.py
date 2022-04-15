from __future__ import unicode_literals
from pprint import pprint
from dataclasses import dataclass
from difflib import SequenceMatcher
import requests
import argparse
import json
import yt_dlp
from tqdm import tqdm


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
    unavailable_reason: str = ""

    def display(self):
        return "Title: '" + self.title + \
            "' from Channel: '" + self.channel + \
            "', URL: " + self.url


def get_playlist_entries(url):
    ydl_opts = {
        'extract_flat': "in_playlist",  # just get video metadata
    }
    with yt_dlp.YoutubeDL(ydl_base_opts | ydl_opts) as ydlp:
        info = ydlp.extract_info(url)
        entries = [
            YoutubeVideo(entry["url"], entry["title"],
                         entry["uploader"])
            for entry in info["entries"]]
        return entries


def get_unavailable_videos(videos):
    ydl_opts = {
        "simulate": True,  # do not actually download anything
    }
    print("Checking whether videos in playlist are available...")
    unavailable_videos = []
    with yt_dlp.YoutubeDL(ydl_base_opts | ydl_opts) as ydlp:
        for entry in tqdm(videos):
            try:
                ydlp.download([entry.url])
                print(".", end="", flush=True)
            except yt_dlp.utils.DownloadError as err:
                entry.unavailable_reason = err.msg
                unavailable_videos.append(entry)
                print("|", end="", flush=True)
    print("\n Finished checking playlist, {} videos unavailable \n".format(
        len(unavailable_videos)))
    return unavailable_videos


def find_alternatives(video: YoutubeVideo):
    with yt_dlp.YoutubeDL(ydl_base_opts) as ydlp:
        suggestions = []
        # search only for video title
        results = ydlp.extract_info(
            f"ytsearch3:{video.title}", download=False)['entries']
        for result in results:
            suggestions.append(YoutubeVideo(
                result["webpage_url"], result["title"], result["channel"]))
        # search for title and channel
        if video.channel:
            query = video.title + " " + video.channel
            results = ydlp.extract_info(
                f"ytsearch3:{query}", download=False)['entries']
            for result in results:
                suggestions.append(YoutubeVideo(
                    result["webpage_url"], result["title"], result["channel"]))

        return suggestions


def find_closest_match(video: YoutubeVideo, playlist):
    closest_video = None
    closest_ratio = -1
    for candidate in playlist:
        if video.url != candidate.url:
            ratio = SequenceMatcher(None, video.title, candidate.title).ratio()
            if ratio > closest_ratio:
                closest_video = candidate
    return closest_video


def suggest_alternatives(video: YoutubeVideo, playlist_entries):
    cyan = "\033[0;36m"
    reset_color = "\033[00m"

    if not video.title or not video.channel:
        # For some videos, youtube doesnt even tell us title/channel anymore
        print(cyan + "A video with the following URL was added to the playlist, but is no longer available:")
        print(video.url + reset_color)
        print("Unfortunately Youtube doesn't tell us the title, so we cannot suggest alternatives. ")
        archived_version = check_wayback(video)
        if archived_version:
            print(
                "The wayback machine seems to have taken a snapshot though, check it out at " + archived_version)
        # TODO get video title from html title
        print("\n")

        return

    alternatives = find_alternatives(video)
    print(cyan + "The following video was added to the playlist, but is no longer available:")
    print(video.display() + reset_color)
    print("Sometimes the reason for unavailablity is helpful: " +
          video.unavailable_reason + ".")
    print("Did you maybe already replace the video in the playlist? By title, the closest match is " +
          find_closest_match(video, playlist_entries).display())
    print("ALternatively, maybe one of the following is a good substitute:")
    for idx, alternative in enumerate(alternatives):
        print(" "*4 + str(idx+1) + ".: " + alternative.display())
    print("\n")


def check_wayback(video: YoutubeVideo):
    url = "https://archive.org/wayback/available?url=" + video.url
    response = requests.get(url)
    if response.status_code == 200 and 'application/json' in response.headers.get('Content-Type', ''):
        decoded = json.loads(response.content.decode('utf-8'))
        snapshot = decoded["archived_snapshots"]
        if snapshot == {}:
            return None
        else:
            return snapshot["closest"]["url"]


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Find alternatives for unavailable videos in a youtube playlist.')
    parser.add_argument(
        "url", help="URL of a non-private playlist", type=str)
    args = parser.parse_args()
    url = args.url
    playlist_entries = get_playlist_entries(url)
    unavailable_videos = get_unavailable_videos(playlist_entries)
    for idx, video in enumerate(unavailable_videos):
        suggest_alternatives(video, playlist_entries)
        if idx != len(unavailable_videos)-1:
            input("Press Enter to go to next unavailable video...")
