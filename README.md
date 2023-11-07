# reader2pinboard.py
Import articles saved to Readwise Reader to Pinboard

- Existing bookmarks are not overwritten
- A successful fetch from the Readwise API saves the current time to a file.On subsequent calls of the script, that value is used to fetch only newer documents.

Usage:
```shell
    export READWISE_API_KEY="your-api-key"
    export PINBOARD_API_TOKEN="your-api-token"
    export READER2PINB_LAST_RUN="/path/to/lastrun/file"
    python3 reader2pinboard.py

    # --dry-run
    # performs a dry run (print information to console instead of adding bookmarks)

    # --all
    # fetches all documents, ignoring any existing timestamp stored in the lastrun file
```