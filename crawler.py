import json
import os
from collections import deque
from re import findall
from time import time, sleep
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

def crawl(api, hashtag, config):
	# print('Crawling started at origin hashtag', origin['user']['username'], 'with ID', origin['user']['pk'])
	if visit_profile(api, hashtag, config):
		pass

def visit_profile(api, hashtag, config):
	while True:
		try:

			processed_tagfeed = {
				'posts' : []
			}
			feed = get_posts(api, hashtag, config)
			print(len(feed))
			profile_dic = {}
			i = 0
			posts = []
			for post in feed:
				if i % 100 == 0:
					print(i)
				posts.append(beautify_post(api, post, profile_dic))
				i+=1
			# posts = [beautify_post(api, post, profile_dic) for post in feed]
			posts = list(filter(lambda x: not x is None, posts))
			if len(posts) < config['min_collect_media']:
				return False
			else:
				processed_tagfeed['posts'] = posts[:config['max_collect_media']]

			try:
				if not os.path.exists(config['profile_path'] + os.sep): os.makedirs(config['profile_path'])  
			except Exception as e:
				print('exception in profile path')
				raise e

			try:
				with open(config['profile_path'] + os.sep + str(hashtag) + '.json', 'w') as file:
					json.dump(processed_tagfeed, file, indent=2)
			except Exception as e:
				print('exception while dumping')
				raise e
		except Exception as e:
			print('exception while visiting profile', e)
			if str(e) == '-':
				raise e
			return False
		else:
			return True

def beautify_post(api, post, profile_dic):
	try:
		keys = post.keys()
		user_id = post['user']['pk']
		processed_media = {
			'username' : post['user']['username'],
			'date' : datetime.datetime.fromtimestamp(post['taken_at']).strftime('%Y/%m/%d %H:%M:%S'),
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

def get_posts(api, hashtag, config):
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
		while next_max_id and len(feed) < config['max_collect_media']:
			print("next_max_id", next_max_id, "len(feed) < max_collect_media", len(feed) < config['max_collect_media'] , len(feed))
			try:
				results = api.feed_tag(hashtag, rank_token, max_id=next_max_id)
			except Exception as e:
				print('exception while getting feed2')
				if str(e) == 'Bad Request: Please wait a few minutes before you try again.':
					sleep(60)
				else:
					continue
					raise e
			feed.extend(results.get('items', []))
			next_max_id = results.get('next_max_id')
		# with open('test.json', 'w') as file:
		# 	json.dump(feed, file, indent=2)
		return feed

	except Exception as e:
		print('exception while getting posts')
		raise e

