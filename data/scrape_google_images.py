"""Scrapes Google Images based on a search query."""

import time
import uuid
import json
import argparse
import requests
from pathlib import Path
from selenium import webdriver

parser = argparse.ArgumentParser()
parser.add_argument('query', type=str, help='The search query to scrape.')
parser.add_argument('output_directory', type=str, help='The directory to output scraped images')
parser.add_argument('--max-images', type=int, default=1000, help='The maximum number of images to scrape.')
args = parser.parse_args()

BASE_URL = 'https://www.google.com/search?q={0}&source=lnms&tbm=isch'
SLEEP_TIME = 0.1

output_directory = Path(args.output_directory)
output_directory.mkdir(parents=True, exist_ok=True)

browser_instance = webdriver.Firefox()
browser_instance.get(BASE_URL.format(args.query))

links = set()
count = 0
offset_index = 0
while len(links) < args.max_images:
    browser_instance.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(SLEEP_TIME)

    thumbnails = browser_instance.find_elements_by_css_selector('img')
    for thumbnail_image in thumbnails[offset_index:len(thumbnails)]:
        try:
            thumbnail_image.click()
            images = browser_instance.find_elements_by_css_selector('img.n3VNCb')
            for image in images:
                src = image.get_attribute('src')
                if src:
                    if src in links: continue
                    links.add(src)

                    filepath = output_directory / '{}_{}.png'.format(args.query, uuid.uuid4())
                    with open(filepath, 'wb+') as file:
                        response = requests.get(src, stream=True)
                        for chunk in response.iter_content(32768):
                            if not chunk: break
                            file.write(chunk)
        except:
            continue

        if len(links) >= args.max_images: break
    offset_index = len(thumbnails)