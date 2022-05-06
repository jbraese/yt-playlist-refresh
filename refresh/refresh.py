from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from wayback import WaybackClient
from bs4 import BeautifulSoup
from refresh.classes import NoTitleInArchiveFailure, NotArchivedFailure, RefreshResult, \
    RefreshSourceAPI, RefreshSourceWayback, RefreshSuccess, YoutubeVideo
from refresh.youtube import get_youtube_search_results


def suggest_alternatives(unavailable_videos: List[YoutubeVideo]) -> List[RefreshResult]:
    """Find alternatives for unavailable videos based on its title and print results"""

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(
            suggest_alternatives_for_one, video) for video in unavailable_videos]
        result_list = []
        print("Waiting for the next suggestions...", end="\r")
        for future in as_completed(futures):
            input("Press Enter to see suggestions for next unavailable video...")
            print("\033[F")  # cursor up one line
            result = future.result()
            result.print_result()
            result_list.append(result)
            print("Waiting for the next suggestions...", end="\r")
    print(" "*50)  # erase last waiting message
    return result_list


def suggest_alternatives_for_one(video: YoutubeVideo) -> RefreshResult:
    """ Try to find alternatives for unavailable video based on its title"""

    if video.title and video.channel:
        return suggest_alternatives_from_title(video)
    else:
        return suggest_alternatives_from_wayback(video)


def suggest_alternatives_from_title(video: YoutubeVideo) -> RefreshResult:
    """Return alternatives for unavailable video for which we know title and channel"""

    alternatives = get_youtube_search_results(video.title, 3)
    alternatives += get_youtube_search_results(video.title + video.channel, 3)
    return RefreshSuccess(video, alternatives, RefreshSourceAPI())


def suggest_alternatives_from_wayback(video: YoutubeVideo) -> RefreshResult:
    """Return alternatives for video based on title of its archived snapshot from Wayback Machine"""

    client = WaybackClient()
    results = client.search(video.url)
    found_snapshot_url = None
    # iterate over all snapshots made of video, starting from the oldest
    for record in results:
        if record.status_code != 200:
            continue
        found_snapshot_url = record.view_url
        # a memento is an archived http response
        response = client.get_memento(record)
        soup = BeautifulSoup(response.text, 'html.parser')

        if hasattr(soup, "title") and soup.title is not None:
            title = clean_wayback_video_title(soup.title.text)
            if len(title) > 0:
                alternatives = get_youtube_search_results(soup.title.text, 6)
                source = RefreshSourceWayback(
                    record.view_url, str(record.timestamp), title)
                return RefreshSuccess(video, alternatives, source)

    if found_snapshot_url is not None:
        return NoTitleInArchiveFailure(video, found_snapshot_url)
    else:
        return NotArchivedFailure(video)


def clean_wayback_video_title(title: str) -> str:
    """Clean archived youtube video title based on simplic heuristic"""

    cleaned = title.strip().lower()
    cleaned = cleaned.removeprefix("youtube").removesuffix(
        "youtube").strip().removesuffix("-")
    return cleaned.strip()
