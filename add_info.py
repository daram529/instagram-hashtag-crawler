#!/usr/bin/python
# -*- coding: utf-8 -*-
# @File Name: add_info.py
# @Created:   2018-04-17 14:30:00  Minkyu Yun (ymk1211@kaist.ac.kr)

import os
import argparse
import multiprocessing as mp
import csv
import sys
from time import time, sleep
from collections import deque
from util import file_to_list
from crawler import crawl
import requests
from urllib.request import urlretrieve
import ast
try:
	from instagram_private_api import (
		Client, __version__ as client_version)
except ImportError:
	import sys
	sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
	from instagram_private_api import (
		Client, __version__ as client_version)

profile_path = '.' + os.path.sep + 'hashtags'			# path where posts are saved

# for comments
included_cols = ['username', 'post_url', 'date', 'media_id']
writer_header = ['username', 'post_url', 'date', 'media_id', "comments"]

# for images
img_config = {
	'image_download' : True,		# download image for single image posts
	'video_download' : True,		# download videos for single video posts
	'carousel_download' : True	# download images/videos for multiple image/video posts
}

def comments_crawl(api, hashtag_path, csv_file_list, csv_write_path):
	for file in csv_file_list:
		if os.path.exists(os.path.join(csv_write_path, file)):
			print("file already exists")
			continue
		reader = csv.reader(open(os.path.join(hashtag_path, file), 'r'))
		next(reader, None)
		writer = csv.DictWriter(open(os.path.join(csv_write_path, file), 'w'), fieldnames = writer_header)
		writer.writeheader()
		i = 0
		for row in reader:
			sys.stdout.write("comments, {}: {} row\r".format(file, i))
			sys.stdout.flush()
			i+=1
			try:
				comments = api.media_n_comments(row[12])
				writer.writerow({'username': row[1], 'post_url': row[2], 'date': row[3], 'media_id': row[12], 'comments': comments})
			except Exception as e:
				print('exception while getting comments')
				raise e
		print("")
   
def images_crawl(api, hashtag_path, csv_file_list, images_path):
	for file in csv_file_list:
		if os.path.exists(os.path.join(images_path, os.path.splitext(file)[0])):
			print("directory already exists")
			continue
		else:
			os.makedirs(os.path.join(images_path, os.path.splitext(file)[0]))


		reader = csv.reader(open(os.path.join(hashtag_path, file), 'r'))
		next(reader, None)
		i = 0
		for row in reader:
			sys.stdout.write("images, {}: {} row\r".format(file, i))
			sys.stdout.flush()
			i+=1
			media_type = row[0]
			if media_type == 'image' and img_config['image_download']:
				url = row[9]
				response = requests.get(url)
				if response.status_code == 200:
				    with open(os.path.join(os.path.join(images_path, os.path.splitext(file)[0]), row[1]+row[3]+".png"), 'wb') as f:
				        f.write(response.content)
				else:
					continue
			elif media_type == 'video' and img_config['video_download']:
				url = row[10]
				try:
					urlretrieve(url, os.path.join(os.path.join(images_path, os.path.splitext(file)[0]), row[1]+row[3]+".mp4"))
				except:
					continue
			elif media_type == 'carousel' and img_config['carousel_download']:
				urls = row[11]
				urls = ast.literal_eval(urls)
				urls = [url.strip() for url in urls]
				j = 0
				for url in urls:
					if '.mp4' in url:
						urlretrieve(url, os.path.join(os.path.join(images_path, os.path.splitext(file)[0]), row[1]+row[3]+"-"+str(j)+".mp4"))
					else:
						response = requests.get(url)
						if response.status_code == 200:
						    with open(os.path.join(os.path.join(images_path, os.path.splitext(file)[0]), row[1]+row[3]+"_"+str(j)+".png"), 'wb') as f:
						        f.write(response.content)
						else:
							continue
					j += 1
		print("")

if __name__ == '__main__':
	# Example command:
	# python examples/savesettings_logincallback.py -u "yyy" -p "zzz" -target "names.txt"
	parser = argparse.ArgumentParser(description='Comments Crawling')
	parser.add_argument('-u', '--username', dest='username', type=str, required=True)
	parser.add_argument('-p', '--password', dest='password', type=str, required=True)
	parser.add_argument('-t', '--target', dest='target', type=str, required=True)
	parser.add_argument('-i', '--type', dest='type', type=str, required=True, default='image')

	args = parser.parse_args()
	try:
		if args.target:
			target = args.target
		else:
			raise Exception('No crawl target given. Provide a hashtag with -t option or file of hashtags with -f')
		print('Client version: %s' % client_version)
		print(target)
		api = Client(args.username, args.password)
	except Exception as e:
		raise Exception("Unable to initiate API:", e)
	else:
		print("Initiating API")


	csv_file_list = []
	if os.path.exists(os.path.join(profile_path, target)):
		hashtag_path = os.path.join(profile_path, target)
		print("hashtag_path:", hashtag_path)

		for file in os.listdir(hashtag_path):
		    if file.endswith(".csv"):
		    	csv_file_list.append(file)

		# comments
		if not os.path.exists(profile_path + os.path.sep + target + "_comments"):
			os.makedirs(profile_path + os.path.sep + target + "_comments")
		csv_write_path = profile_path + os.path.sep + target + "_comments"
		print(csv_write_path)

		# images
		if not os.path.exists(profile_path + os.path.sep + target + "_images"):
			os.makedirs(profile_path + os.path.sep + target + "_images")
		images_path = profile_path + os.path.sep + target + "_images"
		print(images_path)
	else:
		raise Exception("No hashtag folder exists")

	try:
		if args.type in ["image", "images"]:
			images_crawl(api, hashtag_path, csv_file_list, images_path)
		else:
			comments_crawl(api, hashtag_path, csv_file_list, csv_write_path)
	except KeyboardInterrupt:
		print('Comment Crawling terminated')
		print('Images Crawling terminated')
	except Exception as e:
		raise e

# processed_media['comments'] : ["{}: {}".format(comment['user']['username'], comment['text']) for comment in api.media_n_comments(post['caption']['media_id'])] if 'caption' in keys and post['caption'] is not None else ''