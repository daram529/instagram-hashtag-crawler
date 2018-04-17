# Instagram Hashtag Crawler
This crawler was made because most of the crawlers out there seems to either require a browser or a developer account. This Instagram crawler utilizes a private API of Instagram and thus no developer account is required.

Crawler works as follwing:  
1. when crawling a hashtag for the first time, it will crawl as many posts as possible
2. when it stops / run on the same hashtag for the second time, the crawler will crawl posts upto the most recent post saved last time (for example, if crawled upto 2018-04-17, 14:00:00 last time, the crawler will crawl upto this point) and sleep for 30 minutes.  
3. repeat 2 until you manually stop

## Installation
First install [Instagram Private API](https://github.com/ping/instagram_private_api). Kudos for a great project!
```
$ pip install git+https://github.com/ping/instagram_private_api.git
```

Now run `__init__.py`. It'll provide you with the command options. If this shows up, everything probably works
```
$ python __init__.py
usage: __init__.py [-h] -u USERNAME -p PASSWORD [-t TARGET]
```

## Get Crawlin'
To get crawlin', you need to provide your Instagram username and password, and either an Instagram Hashtag without the hash (target) or a text file of the hashtags in each row (targetfile).
Wait a bit and a folder will be made with all the hashtags crawled.

## Options
Inside `__init__.py`, there is a config dictionary. Each config option is explained in the comments. 'batch_size' is number of posts to save in one file.


```
config = {
		'profile_path' : './hashtags',              # Path where output data gets saved
		'batch_size': 1000,							# Number of posts to save in one file(json and csv)
		# 'min_timestamp' : int(time() - 60*60*24*30*12)         # up to how recent you want the posts to be in seconds. If you do not want to use this, put None as value
		'min_timestamp' : None
}
```

## add_info.py
add_info.py downloads comments and images/videos of posts crawled from `__init__.py` and `crawler.py`.  
You need to crawl posts first and then use `add_info.py` to download additional information.

```
$ python add_info.py
usage: add_info.py [-h] -u USERNAME -p PASSWORD -t TARGET -i image or comments
```

You may choose to download either image/video using img_config:

```
img_config = {
	'image_download' : True,		# download image for single image posts
	'video_download' : True,		# download videos for single video posts
	'carousel_download' : True	# download images/videos for multiple image/video posts
}
```