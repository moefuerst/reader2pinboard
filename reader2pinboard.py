#!/usr/bin/env python3
"""
Imports articles saved to Readwise Reader to Pinboard
- Existing bookmarks are not overwritten
- A successful fetch from the Readwise API saves the current time to a file.
  On subsequent calls of the script, that value is used to fetch only newer
  documents.

Usage:
    export READWISE_API_KEY="your-api-key"
    export PINBOARD_API_TOKEN="your-api-token"
    export READER2PINB_LAST_RUN="/path/to/lastrun/file"
    python3 reader2pinboard.py

    --dry-run
    performs a dry run (print information to console instead of adding bookmarks)

    --all
    fetches all documents, ignoring any existing timestamp stored in the lastrun
    file
"""
import os
import argparse
import requests
import time
from datetime import datetime
from dateutil import parser

# Read API keys from environment variables
READWISE_API_KEY = os.environ.get('READWISE_API_KEY')
PINBOARD_API_TOKEN = os.environ.get('PINBOARD_API_TOKEN')

if READWISE_API_KEY is None or PINBOARD_API_TOKEN is None:
    print("Please set READWISE_API_KEY and PINBOARD_API_TOKEN environment variables.")
    exit(1)

# Readwise API endpoint for the Readwise Reader API
READWISE_API_URL = 'https://readwise.io/api/v3/list/'

# Pinboard API endpoint to add bookmarks
PINBOARD_API_URL = 'https://api.pinboard.in/v1/posts/add'

# Source tag to be added to each bookmark, can add several separated by whitespace
ADDITIONAL_TAGS = '.from:Reader'

# File path for storing the last run timestamp
LAST_RUN_FILE = os.environ.get('READER2PINB_LAST_RUN')
if LAST_RUN_FILE is None:
    LAST_RUN_FILE = 'lastrun'


def get_last_run_timestamp():
    try:
        with open(LAST_RUN_FILE, 'r') as file:
            timestamp = file.read()
            return timestamp
    except FileNotFoundError:
        return None


def set_last_run_timestamp(timestamp):
    with open(LAST_RUN_FILE, 'w') as file:
        file.write(timestamp)


def format_created_at(created_at):
    readwise_datetime = parser.parse(created_at)
    pinboard_datetime = readwise_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
    return pinboard_datetime


def get_new_readwise_documents():
    last_run_timestamp = get_last_run_timestamp()

    new_data = fetch_reader_document_list_api(updated_after=last_run_timestamp)

    if new_data:
        print(f"{len(new_data)} documents returned from Readwise API.")
        set_last_run_timestamp(datetime.now().isoformat())
        return new_data
    else:
        print("Failed to fetch documents from Readwise API.")
        return []


def add_bookmark_to_pinboard(title, url, document, tags, created_at):
    if isinstance(tags, dict):
        tags = list(tags.keys())

    # Pinboard tags cannot have whitespace
    tags_str = ' '.join([tag.replace(' ', '') for tag in tags])

    # Filter out documents with "category" set to "highlight", feed entries, or empty "source_url"
    category = document.get('category')
    location = document.get('location')
    source_url = document.get('source_url')
    if category == 'highlight' or location == 'feed' or not source_url:
        print(f"Ignoring document: {title} (category: {category}, location: {location}, source_url: {source_url})")
        return

    extended_info = f"{document.get('summary', '')}\nby {document.get('author', '')}, {document.get('site_name', '')}"

    if DRY_RUN:
        print(f"Title: {title}")
        print(f"URL: {url}")
        print(f"Extended: {extended_info}")
        print(f"Tags: {tags_str}")
        print(f"dt: {format_created_at(created_at)}")
        print(f"Adding bookmark to Pinboard (dry run)")
    else:
        params = {
            'auth_token': PINBOARD_API_TOKEN,
            'format': 'json',
            'url': url,
            'description': title[:255],         # Ensure title is not over 255 characters
            'extended': extended_info[:65536],  # Ensure extended info is not over 65536 characters
            'tags': ADDITIONAL_TAGS + " " + tags_str,
            'replace': 'no',                    # Do not overwrite existing bookmarks
            'dt': format_created_at(created_at)
        }

        response = requests.get(PINBOARD_API_URL, params=params)

        if response.status_code == 200:
            print(f"Bookmark added to Pinboard: {title}")
        else:
            print(f"Failed to add bookmark to Pinboard. Status Code: {response.status_code}")

        # Sleep for at least 3 seconds to respect the rate limit
        time.sleep(3)


# Readwise Reader API ""SDK""
# https://readwise.io/reader_api
def fetch_reader_document_list_api(updated_after=None, location=None):
    full_data = []
    next_page_cursor = None
    while True:
        params = {}
        if next_page_cursor:
            params['pageCursor'] = next_page_cursor
        if updated_after:
            params['updatedAfter'] = updated_after
        if location:
            params['location'] = location
        print("Making export API request with params " + str(params) + "...")
        response = requests.get(
            url=READWISE_API_URL,
            params=params,
            headers={"Authorization": f"Token {READWISE_API_KEY}"}
        )
        if 'results' in response.json():
            full_data.extend(response.json()['results'])
        next_page_cursor = response.json().get('nextPageCursor')
        if not next_page_cursor:
            break
    return full_data


if __name__ == "__main__":
    aparser = argparse.ArgumentParser(description='Add Readwise documents as bookmarks to Pinboard')
    aparser.add_argument('--dry-run', action='store_true', help='Perform a dry run (print information to console)')
    aparser.add_argument('--all', action='store_true', help='Fetch all documents, ignoring the last run timestamp')

    args = aparser.parse_args()
    DRY_RUN = args.dry_run

    if args.all:
        set_last_run_timestamp(None)

    new_documents = get_new_readwise_documents()

    for document in new_documents:
        try:
            title = document.get('title')
            url = document.get('source_url')
            tags = document.get('tags', [])
            created_at = document.get('created_at')

            add_bookmark_to_pinboard(title, url, document, tags, created_at)
        except:
            pass
