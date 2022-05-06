from argparse import ArgumentParser
from refresh.youtube import get_playlist_entries, get_unavailable_videos
from refresh.refresh import suggest_alternatives

if __name__ == "__main__":

    parser = ArgumentParser(
        description='Find alternatives for unavailable videos in a youtube playlist.')
    parser.add_argument(
        "url", help="URL of a non-private playlist", type=str)
    args = parser.parse_args()
    url = args.url

    print("In order to refresh your playlist, we will try to find alternatives to its unavailable videos.", flush=True)

    playlist_entries = get_playlist_entries(url)
    print("Playlist contains {} videos, now checking which are available".format(
        len(playlist_entries)))

    unavailable_videos = get_unavailable_videos(playlist_entries)
    print("\n Finished checking playlist, {} videos unavailable \n".format(
        len(unavailable_videos)), flush=True)

    alternatives = suggest_alternatives(unavailable_videos)
