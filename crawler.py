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
import sys

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
	if prev_time is not None:
		print("Crawling posts upto the time:", prev_time)
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
			'post_url': "https://www.instagram.com/p/" + post['code'],
			'taken_at': post['taken_at'],
			'username' : post['user']['username'],
			'date' : datetime.datetime.fromtimestamp(post['taken_at']).strftime('%Y-%m-%dT%H:%M:%S'),
			'like_count' : post['like_count'] if 'like_count' in keys else 0,
			'comment_count' : post['comment_count'] if 'comment_count' in keys else 0,
			'caption' : post['caption']['text'] if 'caption' in keys and post['caption'] is not None else '',
			'media_id' : post['caption']['media_id'] if 'caption' in keys and post['caption'] is not None else ''
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
			processed_media['carousel_urls'] = urls
		# processed_media['comments'] : ["{}: {}".format(comment['user']['username'], comment['text']) for comment in api.media_n_comments(post['caption']['media_id'])] if 'caption' in keys and post['caption'] is not None else ''
		return processed_media
	except Exception as e:
		print('exception in beautify post')
		return processed_media

def get_posts(api, hashtag, config, mode='initial', prev_time=0):
	failures = 0
	total_count = 0
	start_time = time()
	try:
		feed = []
		rank_token = api.generate_uuid()
		try:
			results = api.feed_tag(hashtag, rank_token, min_timestamp=config['min_timestamp'])
		except Exception as e:
			print('exception while getting feed1')
			raise e
		feed.extend(results.get('items', []))

		batch_time = time()
		next_max_id = results.get('next_max_id')
		while next_max_id:
			current_time = time()
			# print("hashtag:", hashtag, "/ current_no._posts:", len(feed), "/ total_no._posts:", total_count + len(feed), "/ time_elapsed(sec):", time()-start_time, "/ batch_speed:", (total_count + len(feed))/(time()-batch_time), "posts per sec")
			sys.stdout.write("hashtag: {} / current batch posts: {} out of {} / total posts: {} / time_elasped: {}h {}m {:.3f}s / batch_speed: {:.3f} posts per sec\r".format(hashtag, len(feed), config['batch_size'], total_count + len(feed), (current_time-start_time)//3600, (current_time-start_time)//60, (current_time-start_time)%60, len(feed) / (time()-batch_time)))
			sys.stdout.flush()
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
			feed.extend(results.get('items', []))
			next_max_id = results.get('next_max_id')
			if failures > 5:
				# Too much failures. Should stop now
				save_partial(api, hashtag, config, feed)
				return
			elif mode == 'initial' and len(feed) > config['batch_size']:
				# dump config['batch_size'] at a time at initial --> can change to 'initial_batch_size' is needed
				save_partial(api, hashtag, config, feed)
				total_count += len(feed)
				batch_time = time()
				feed = []
			elif mode == 'surface' and len(feed) > config['batch_size']:
				# dump config['batch_size'] at a time at surface --> can change to 'surface_batch_size' is needed
				timeouts = save_partial(api, hashtag, config, feed, prev_time=prev_time)
				if timeouts > config['batch_size'] / 2:
					print("sutface mode: reached overlapping posts. ==> timeout")
					return feed
				total_count += len(feed)
				batch_time = time()
				feed = []
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
	print("")
	if prev_time is not None:
		# If prev_time is provided, it means it's surface crawlng
		# --> filter out the ones that are from before prev_time
		timeouts = len(list(filter(lambda x: x['date'] < prev_time, posts)))
		posts = list(filter(lambda x: x['date'] > prev_time, posts))
		print("Savings... timeout posts: {} / saved posts: {} out of {}".format(timeouts, len(posts), timeouts+len(posts)))
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
		with open(config['profile_path'] + os.sep + str(hashtag) + os.sep + file_name + '.json', 'w') as file:
			json.dump({'posts': posts}, file, indent=2)

		# CSV
		all_fields = ["post_type", "username", "post_url", "date", "taken_at", "like_count", "comment_count", "caption","tags", "pic_url", "vedio_url", "carousel_urls", "media_id"]
		with open(config['profile_path'] + os.sep + str(hashtag) + os.sep + file_name + '.csv', 'w') as csv_file:
			csv_writer = csv.DictWriter(csv_file, all_fields)
			csv_writer.writeheader()
			for post in posts:
				csv_writer.writerow(post)

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
	file_list.sort()
	if file_list is None or len(file_list) == 0:
		return None
	recent_time, _ = os.path.splitext(file_list[-1])
	return recent_time
