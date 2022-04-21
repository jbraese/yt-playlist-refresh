# yt-playlist-refresh

Do you ever wonder how many songs you have forgotten because Youtube removed their videos from your playlists? 

This tool is here to help. It takes a non-private Youtube playlist, identifies videos that were once added to the playlist but are no longer available, and tries to suggest available alternative videos that you can add instead. For that, it looks at Youtube (via [yt-dlp](https://github.com/yt-dlp/yt-dlp)) and the Internet Archive's [Wayback Machine](https://web.archive.org/). Note that to not mess up your playlist, the tool just presents you with suggestions which you can then manually add to your playlists. 

If you use conda, you can install all required dependencies from the `environment.yml` file in this repo by running `conda env create -f environment.yml`. You can then start to refresh your playlist by running `python main.py <your-playlist-url>`. 
