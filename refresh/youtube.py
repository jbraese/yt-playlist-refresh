from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple
import yt_dlp
from refresh.classes import YoutubeVideo


class MyLogger(object):
    # TODO proper logging?
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


ydl_base_opts = {
    'logger': MyLogger(),
}


def get_playlist_entries(url: str) -> List[YoutubeVideo]:
    """Return list of all available and unavailable videos from a yt playlist url"""

    ydl_opts = {
        'extract_flat': "in_playlist",  # just get video metadata
    }
    with yt_dlp.YoutubeDL(ydl_base_opts | ydl_opts) as ydlp:
        info = ydlp.extract_info(url)
        return [YoutubeVideo(entry["url"], entry["title"], entry["uploader"])
                for entry in info["entries"]]


# TODO this is very slow
# could replace w regular request and parse html to see if available
def is_video_available(video: YoutubeVideo) -> Tuple[bool, YoutubeVideo]:
    """Check whether a video is still available on Youtube or not"""

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
    """Return only the unavailable videos from a list, while printing progress"""

    unavailable_videos = []
    digits = len(str(len(videos)))
    print("{} of {} done".format(str(0).zfill(
        digits), len(videos)), flush=True, end="")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(
            is_video_available, video) for video in videos]
        for idx, future in enumerate(as_completed(futures)):
            if idx % 10 == 0:
                print("\033[F")  # cursor up one line
                print("{} of {} done".format(str(idx).zfill(
                    digits), len(videos)), flush=True, end="")
            available, video = future.result()
            if not available:
                unavailable_videos.append(video)
    print("\033[F")  # cursor up one line
    print("{}".format(str(len(videos)).zfill(digits)), flush=True)
    return unavailable_videos


def get_youtube_search_results(query: str, number_results: int = 6) -> List[YoutubeVideo]:
    """Search youtube for <query> and return top <number_results> videos"""

    with yt_dlp.YoutubeDL(ydl_base_opts) as ydlp:
        results = ydlp.extract_info(
            f"ytsearch{str(number_results)}:{query}", download=False)['entries']
        return [YoutubeVideo(entry["webpage_url"], entry["title"], entry["channel"])
                for entry in results]
