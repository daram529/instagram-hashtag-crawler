import json
import os
from functools import reduce
from collections import deque
from re import findall
from time import time, sleep, strftime, localtime
import datetime
from util import randselect, byteify, file_to_list
import csv
import queue

"""
Things to do

1. pciture?
2. carousel? (video or more than one photo)
3. json to csv
4. threading for differnet hashtags
5. get_posts / beautify_post threading
"""

def crawl(api, hashtag, config, mode='initial'):
	if mode == 'initial':
		if os.path.exists(config['profile_path'] + os.sep):
			if os.path.exists(config['profile_path'] + os.sep + hashtag):
				if len(os.listdir(config['profile_path'] + os.sep + hashtag)) > 0:
					print('There exists previous files. Now starting surface crawling.')
					print('DIR: ' + config['profile_path'] + os.sep + hashtag)
					mode = 'surface'
	# print('Crawling started at origin hashtag', origin['user']['username'], 'with ID', origin['user']['pk'])
	if visit_profile(api, hashtag, config, mode):
		pass

def visit_profile(api, hashtag, config, mode='initial'):
	# Now crawling happens in get_posts
	prev_time = latest_time(hashtag, config)
	while True:
		try:
			processed_tagfeed = {
				'posts' : []
			}
			feed = get_posts(api, hashtag, config, mode, prev_time)
		except Exception as e:
			print('exception while visiting profile', e)
			if str(e) == '-':
				raise e
			return False
		else:
			return True

def beautify_post(api, post, profile_dic):
	#%y-%m-%dT%H:%M
	try:
		keys = post.keys()
		user_id = post['user']['pk']
		processed_media = {
			'url': "https://www.instagram.com/p/" + post['code'],
			'taken_at': post['taken_at'],
			'username' : post['user']['username'],
			'date' : datetime.datetime.fromtimestamp(post['taken_at']).strftime('%Y-%m-%dT%H:%M:%S'),
			'like_count' : post['like_count'] if 'like_count' in keys else 0,
			'comment_count' : post['comment_count'] if 'comment_count' in keys else 0,
			'caption' : post['caption']['text'] if 'caption' in keys and post['caption'] is not None else ''
		}
		processed_media['tags'] = findall(r'#[^#\s]*', processed_media['caption'])

		if post['media_type'] == 1:
			processed_media['post_type'] = "image"
			processed_media['pic_url'] = post['image_versions2']['candidates'][0]['url']
		elif post['media_type'] == 2:
			processed_media['post_type'] = "video"
			processed_media['vedio_url'] = post['video_versions'][0]['url']
		else:
			processed_media['post_type'] = "carousel"
			urls = []
			for one_post in post['carousel_media']:
				if one_post['media_type'] == 1:
					urls.append(one_post['image_versions2']['candidates'][0]['url'])
				else:
					urls.append(one_post['video_versions'][0]['url'])
			processed_media['urls'] = urls
		# processed_media['comments'] : ["{}: {}".format(comment['user']['username'], comment['text']) for comment in api.media_n_comments(post['caption']['media_id'])] if 'caption' in keys and post['caption'] is not None else ''
		return processed_media
	except Exception as e:
		print('exception in beautify post')
		return processed_media

def get_posts(api, hashtag, config, mode='initial', prev_time=0):
	failures = 0
	count = 0
	try:
		feed = []
		rank_token = api.generate_uuid()
		try:
			results = api.feed_tag(hashtag, rank_token, min_timestamp=config['min_timestamp'])
		except Exception as e:
			print('exception while getting feed1')
			raise e
		feed.extend(results.get('items', []))

		if config['min_timestamp'] is not None: return feed

		next_max_id = results.get('next_max_id')
		while next_max_id and count < config['max_collect_media']:
			print("next_max_id", next_max_id, "len(feed) < max_collect_media", len(feed) < config['max_collect_media'] , len(feed))
			try:
				results = api.feed_tag(hashtag, rank_token, max_id=next_max_id)
				failures = 0
			except Exception as e:
				print('exception while getting feed- timeout')
				failures += 1
				if str(e) == 'Bad Request: Please wait a few minutes before you try again.':
					sleep(60)
				else:
					continue
					raise e
			count += 1
			feed.extend(results.get('items', []))
			next_max_id = results.get('next_max_id')
			if failures > 5:
				# Too much failures. Should stop now
				save_partial(api, hashtag, config, feed)
				return
			elif mode == 'initial' and len(feed) > config['batch_size']:
				# dump config['batch_size'] at a time at initial --> can change to 'initial_batch_size' is needed
				save_partial(api, hashtag, config, feed)
				feed = []
			elif mode == 'surface' and len(feed) > config['batch_size']:
				# dump config['batch_size'] at a time at surface --> can change to 'surface_batch_size' is needed
				timeouts = save_partial(api, hashtag, config, feed, prev_time=prev_time)
				if timeouts > config['batch_size'] / 10:
					return feed
				feed = []
		# with open('test.json', 'w') as file:
		# 	json.dump(feed, file, indent=2)
		return feed

	except Exception as e:
		print('exception while getting posts')
		raise e

def save_partial(api, hashtag, config, feed, prev_time=None):
	# Saves config['batch_size'] feeds
	posts = []
	timeouts = 0
	curr_time = time()
	for post in feed:
		posts.append(beautify_post(api, post, {}))
	posts = list(filter(lambda x: x is not None, posts))
	if prev_time is not None:
		# If prev_time is provided, it means it's surface crawlng
		# --> filter out the ones that are from before prev_time
		time_count = len(list(filter(lambda x: x['taken_at'] < prev_time, posts)))
		posts = list(filter(lambda x: x['taken_at'] > prev_time, posts))
	try:
		if not os.path.exists(config['profile_path'] + os.sep):
			os.makedirs(config['profile_path'])
		if not os.path.exists(config['profile_path'] + os.sep + hashtag):
			os.makedirs(config['profile_path'] + os.sep + hashtag)
	except Exception as e:
		print('exception in profile path ')
		raise e
	# file_name is from the latest time found in the feeds
	file_date = reduce(lambda x, y: max(x, y), [post['taken_at'] for post in posts])
	file_name = strftime('%Y-%m-%dT%H:%M:%S', localtime(file_date))
	try:
		with open(config['profile_path'] + os.sep + str(hashtag) + '/' + file_name + '.json', 'w') as file:
			json.dump({'posts': posts}, file, indent=2)
	except Exception as e:
		print('exception while dumping')
		raise e
	return timeouts

def latest_time(hashtag, config):
	# Finds the latest YYYY-mm-DDTHH-MM-SS.json from the directory
	# and returns the latest time
	try:
		if not os.path.exists(config['profile_path'] + os.sep):
			os.makedirs(config['profile_path'])
		if not os.path.exists(config['profile_path'] + os.sep + hashtag):
			os.makedirs(config['profile_path'] + os.sep + hashtag)
	except Exception as e:
		print('exception in profile path')
		raise e
	file_list = os.listdir(config['profile_path'] + os.sep + hashtag)
	file_list = list(filter(lambda x: x[-4:] == 'json', file_list)).sort()
	if file_list is None or len(file_list) == 0:
		return None
	with open(config['profile_path'] + os.sep + hashtag + os.sep + file_list[-1]) as f:
		data = json.load(f)
	return file_list[-1]
	# below is reducing for
	# return reduce(lambda x, y: max(x, y), [post['taken_at'] for post in data['posts']])
