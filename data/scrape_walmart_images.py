"""Scrape product images from Walmart."""

import uuid
import tqdm
import requests
import argparse
import mimetypes
from enum import Enum
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import (
    urlencode,
    unquote,
    urlparse,
    parse_qsl,
    ParseResult,
    quote as urlquote
)

class WalmartSource(Enum):
    """Source to scrape images from."""
    WALMART_CA = 'ca'
    WALMART_COM = 'com'

parser = argparse.ArgumentParser(description='Scrape product images from Walmart.')
parser.add_argument('query', type=str, help='The search query to scrape.')
parser.add_argument('output_directory', type=Path, help='The directory to output scraped images')
parser.add_argument('--sources', type=WalmartSource, nargs='+', choices=list(WalmartSource), default=[
                    WalmartSource.WALMART_CA, WalmartSource.WALMART_COM],
                    help='The source to scrape images from (i.e. the Walmart site(s)). Defaults to '
                    'Canadian Walmart (https://walmart.ca) and American Walmart (https://walmart.com).')
parser.add_argument('--chunk-size', '-cz', type=int, default=32768, help='The number of bytes to save at a time.')
parser.add_argument
args = parser.parse_args()

def add_url_params(url, **params):
    """
    Add GET params to provided URL being aware of existing.

    Source code from https://stackoverflow.com/a/25580545/7614083.

    :param url: string of target URL
    :param **params: dict containing requested params to be added
    :return: string with updated URL

    >> url = 'http://stackoverflow.com/test?answers=true'
    >> new_params = {'answers': False, 'data': ['some','values']}
    >> add_url_params(url, **new_params)
    'http://stackoverflow.com/test?data=some&data=values&answers=false'
    """
    # Unquoting URL first so we don't loose existing args
    url = unquote(url)
    # Extracting url info
    parsed_url = urlparse(url)
    # Extracting URL arguments from parsed URL
    get_args = parsed_url.query
    # Converting URL arguments to dict
    parsed_get_args = dict(parse_qsl(get_args))
    # Merging URL arguments dict with new params
    parsed_get_args.update(params)

    # Bool and Dict values should be converted to json-friendly values
    parsed_get_args.update(
        {k: dumps(v) for k, v in parsed_get_args.items()
         if isinstance(v, (bool, dict))}
    )

    # Converting URL argument to proper query string
    encoded_get_args = urlencode(
        parsed_get_args,
        doseq=True,
        quote_via=urlquote
    )

    # Creating new parsed result object based on provided with new
    # URL arguments. Same thing happens inside of urlparse.
    new_url = ParseResult(
        parsed_url.scheme, parsed_url.netloc, parsed_url.path,
        parsed_url.params, encoded_get_args, parsed_url.fragment
    ).geturl()

    return new_url

def get_bs4(url, **params):
    """Return the BeautifulSoup instance given a url and parameters."""
    DEFAULT_HEADERS = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '3600',
        # Emulate Gecko agent
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'
    }

    request = requests.get(add_url_params(url, **params), DEFAULT_HEADERS)
    return BeautifulSoup(request.content, 'html.parser')

def get_walmart_image(image_url):
    """
    Return the original image URL from a Walmart thumbnail image URL.
    If the original could not be found, return None.
    """
    # There are two types of Walmart image CDNs: walmart.ca and walmart.com.
    # They both store images in a slightly different way:
    # * The canadian CDN allows you to specifiy, in the url,
    #   whether to return a thumnail or the original.
    # * The american CDN uses GET params to specify the size of
    #   the returned image.
    if '.ca' in image_url and 'Thumbnails' in image_url:
        # The URL is of the form: "https://i5.walmartimages.ca/images/Thumbnails/**.jpg"
        return image_url.replace('Thumbnails/', 'Enlarge/')

    if '.com/asr/' in image_url:
        # We want to remove the following parameters: odnWidth and odnHeight
        return add_url_params(image_url, odnWidth='', odnHeight='')

    # Return None if the image URL could not be parsed.
    return None

def scrape_walmart_ca():
    """Scrape from Walmart.ca."""
    ROOT_URL = 'https://www.walmart.ca/search'

    # Get max page
    max_page = None
    soup = get_bs4(ROOT_URL, q=args.query)
    pages = [int(span.text)
        for span in soup.findAll('span', {'class': 'css-ijjviy ed60zyg11'})
        if span.text.isnumeric()
    ]

    if len(pages) > 0:
        max_page = max(pages)

    result = set()
    with tqdm.tqdm(total=max_page) as progress:
        while max_page is None or progress.n < max_page:
            page = progress.n + 1
            soup = get_bs4(ROOT_URL, q=args.query, p=page)
            products = soup.findAll('div', {
                'class': 'css-x7wixz epettpn0',
                'data-automation': 'product'
            })

            if len(products) == 0:
                break

            for product in products:
                image = product.find('img', {'class': 'css-gxbcya e175iya62'})
                image_url = get_walmart_image(image['src'])
                if image_url is None: continue
                result.add(image_url)

            progress.update(1)

    return result

def scrape_walmart_com():
    """Scrape from Walmart.com."""
    ROOT_URL = 'https://www.walmart.com/search/'

    # Get max page
    while True:
        max_page = None
        soup = get_bs4(ROOT_URL, query=args.query, page=1, ps=40)
        paginator_list = soup.find('ul', {'class': 'paginator-list'})
        if paginator_list is None: continue

        pages = [int(a.text)
            for a in [li.find('a') for li in paginator_list.findAll('li')]
            if a is not None and a.text.isnumeric()
        ]

        if len(pages) > 0:
            max_page = max(pages)

        break

    result = set()
    with tqdm.tqdm(total=max_page) as progress:
        while max_page is None or progress.n < max_page:
            page = progress.n + 1
            while True:
                soup = get_bs4(ROOT_URL, query=args.query, page=page, ps=40)
                images = soup.findAll('img', {
                    'data-pnodetype': 'item-pimg'
                })

                if len(images) > 0: break
                if len(images) == 0 and max_page is None:
                    progress.n = max_page
                    break

            for image in images:
                image_url = get_walmart_image(image['src'])
                if image_url is None: continue
                result.add(image_url)

            progress.update(1)

    return result


# Map each source to a function
_SOURCE_HANDLERS = {
    WalmartSource.WALMART_CA: scrape_walmart_ca,
    WalmartSource.WALMART_COM: scrape_walmart_com
}

result = set()
for source in args.sources:
    source_name = 'Walmart.' + source.value
    print(f'Scraping "{args.query}" from {source_name}')
    result.update(_SOURCE_HANDLERS[source]())

# Download images
print(f'Downloading and saving images to {args.output_directory}')
args.output_directory.mkdir(parents=True, exist_ok=True)

for url in tqdm.tqdm(result):
    response = requests.get(url, stream=True)
    extension = mimetypes.guess_extension(response.headers['content-type'])
    filepath = args.output_directory / f'{uuid.uuid4()}{extension}'
    with open(filepath, 'wb+') as file:
        for chunk in response.iter_content(args.chunk_size):
            if not chunk: break
            file.write(chunk)