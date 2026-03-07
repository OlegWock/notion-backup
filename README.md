# notion-backup

Export your Notion workspace to a local zip file.

## Setup

```
uv sync
cp .env.example .env
# Fill in your credentials in .env
```

### Getting credentials

- **NOTION_TOKEN_V2**: Open Notion in browser → DevTools → Application → Cookies → `token_v2`
- **NOTION_SPACE_ID**: DevTools → Network → any Notion API request → look for `spaceId` in the payload

## Usage

```
uv run main.py
```

The export zip will be saved to `./downloads/`.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `NOTION_SPACE_ID` | *(required)* | Workspace ID |
| `NOTION_TOKEN_V2` | *(required)* | Auth token from browser cookie |
| `NOTION_EXPORT_TYPE` | `markdown` | `markdown` or `html` |
| `NOTION_FLATTEN_EXPORT_FILETREE` | `false` | Flatten nested page structure |
| `NOTION_EXPORT_COMMENTS` | `true` | Include comments in export |
| `DOWNLOADS_DIRECTORY_PATH` | `./downloads` | Where to save the zip |
