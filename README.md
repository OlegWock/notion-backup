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

### Local

```
uv run main.py
```

All settings can be passed as CLI arguments, environment variables, or via `.env` file. CLI arguments take precedence over env vars.

```
uv run main.py --space-id XXX --token YYY --export-type html --flatten --no-comments --output-dir ./out
```

### Docker

```
docker compose run --rm notion-backup
```

### Scheduled backups (Docker with cron)

Set `CRON_SCHEDULE` to run backups on a schedule. The container runs one backup immediately, then starts cron.

```yaml
# docker-compose.yml
services:
  notion-backup:
    build: .
    env_file: .env
    environment:
      CRON_SCHEDULE: "0 3 * * *"  # daily at 3am
    volumes:
      - ./downloads:/app/downloads
```

```
docker compose up -d notion-backup
```

## Configuration

All options can be set via CLI arguments, environment variables, or `.env` file.

| CLI arg | Env variable | Default | Description |
|---|---|---|---|
| `--space-id` | `NOTION_SPACE_ID` | *(required)* | Workspace ID |
| `--token` | `NOTION_TOKEN_V2` | *(required)* | Auth token from browser cookie |
| `--export-type` | `NOTION_EXPORT_TYPE` | `markdown` | `markdown` or `html` |
| `--flatten` | `NOTION_FLATTEN_EXPORT_FILETREE` | `false` | Flatten nested page structure |
| `--no-comments` | `NOTION_EXPORT_COMMENTS` | `true` | Include comments in export |
| `--output-dir` | `DOWNLOADS_DIRECTORY_PATH` | `./downloads` | Where to save the zip |
| `--output-filename` | `NOTION_EXPORT_FILENAME` | *(auto)* | Fixed filename (overwrites previous) |
| | `CRON_SCHEDULE` | | Cron expression for scheduled backups (Docker only) |
