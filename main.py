import sys
import time
import logging
import uuid
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

NOTION_API_BASE = "https://www.notion.so/api/v3"
POLL_INTERVAL_SECONDS = 5
MAX_POLL_ATTEMPTS = 500


def trigger_export_task(
    client: httpx.Client,
    space_id: str,
    export_type: str,
    flatten: bool,
    export_comments: bool,
) -> tuple[str, int]:
    """Triggers a Notion workspace export. Returns (task_id, trigger_timestamp_ms)."""
    payload = {
        "task": {
            "eventName": "exportSpace",
            "request": {
                "spaceId": space_id,
                "shouldExportComments": export_comments,
                "exportOptions": {
                    "exportType": export_type,
                    "flattenExportFiletree": flatten,
                    "timeZone": "Europe/Berlin",
                    "locale": "en",
                },
            },
        }
    }

    trigger_time = int(time.time() * 1000)
    resp = client.post(f"{NOTION_API_BASE}/enqueueTask", json=payload)
    resp.raise_for_status()
    data = resp.json()

    if "errorId" in data:
        raise RuntimeError(f"Notion API error: {data.get('message', data)}")

    task_id = data.get("taskId", "unknown")
    log.info("Export task triggered, taskId: %s", task_id)
    return task_id, trigger_time


def poll_for_download_url(
    client: httpx.Client,
    space_id: str,
    trigger_time_ms: int,
) -> tuple[str, str | None]:
    """Polls Notion notifications until the export download link is available.
    Returns (download_url, notification_id)."""
    payload = {
        "spaceId": space_id,
        "size": 20,
        "type": "unread_and_read",
        "variant": "no_grouping",
    }

    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        time.sleep(POLL_INTERVAL_SECONDS)
        resp = client.post(f"{NOTION_API_BASE}/getNotificationLogV2", json=payload)
        resp.raise_for_status()
        data = resp.json()

        notifications = data.get("recordMap", {}).get("notification", {})
        activities = data.get("recordMap", {}).get("activity", {})

        for activity_id, activity in activities.items():
            value = activity.get("value", {})
            try:
                start_time = int(value.get("start_time", 0))
            except (ValueError, TypeError):
                continue
            if start_time < trigger_time_ms:
                continue

            edits = value.get("edits", [])
            if edits and edits[0].get("link"):
                url = edits[0]["link"]
                log.info("Download URL available after %d attempts", attempt)

                # Find the notification ID that references this activity
                notification_id = None
                for nid, notif in notifications.items():
                    nval = notif.get("value", {})
                    if nval.get("activity_id") == activity_id:
                        notification_id = nid
                        break

                return url, notification_id

        if attempt % 10 == 0:
            log.info("Still waiting for export... (attempt %d/%d)", attempt, MAX_POLL_ATTEMPTS)

    raise TimeoutError(
        f"Export did not complete after {MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS}s"
    )


def archive_notification(
    client: httpx.Client,
    space_id: str,
    notification_id: str,
) -> None:
    """Marks the export notification as read and archived."""
    payload = {
        "requestId": str(uuid.uuid4()),
        "transactions": [
            {
                "id": str(uuid.uuid4()),
                "spaceId": space_id,
                "operations": [
                    {
                        "command": "update",
                        "pointer": {
                            "table": "notification",
                            "id": notification_id,
                            "spaceId": space_id,
                        },
                        "path": [],
                        "args": {
                            "visited": True,
                            "read": True,
                            "archived_at": int(time.time() * 1000),
                        },
                    }
                ],
            }
        ],
        "unretryable_error_behavior": "continue",
    }

    resp = client.post(f"{NOTION_API_BASE}/saveTransactionsMain", json=payload)
    resp.raise_for_status()
    log.info("Export notification archived")


def download_file(client: httpx.Client, url: str, dest: Path) -> Path:
    """Downloads the export zip to the given path."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    log.info("Downloading to: %s", dest)

    with client.stream("GET", url) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=8192):
                f.write(chunk)

    log.info("Download complete: %s (%.2f MB)", dest.name, dest.stat().st_size / 1024 / 1024)
    return dest


def main():
    load_dotenv()

    space_id = os.environ.get("NOTION_SPACE_ID")
    token = os.environ.get("NOTION_TOKEN_V2")
    if not space_id or not token:
        log.error("NOTION_SPACE_ID and NOTION_TOKEN_V2 environment variables are required")
        sys.exit(1)

    export_type = os.environ.get("NOTION_EXPORT_TYPE", "markdown")
    flatten = os.environ.get("NOTION_FLATTEN_EXPORT_FILETREE", "false").lower() == "true"
    export_comments = os.environ.get("NOTION_EXPORT_COMMENTS", "true").lower() == "true"
    downloads_dir = Path(os.environ.get("DOWNLOADS_DIRECTORY_PATH", "./downloads"))

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    flatten_suffix = "-flattened" if flatten else ""
    filename = f"notion-export-{export_type}{flatten_suffix}_{timestamp}.zip"
    dest_path = downloads_dir / filename

    client = httpx.Client(
        cookies={"token_v2": token},
        timeout=60,
        follow_redirects=True,
    )

    try:
        _task_id, trigger_time = trigger_export_task(
            client, space_id, export_type, flatten, export_comments
        )
        download_url, notification_id = poll_for_download_url(client, space_id, trigger_time)
        download_file(client, download_url, dest_path)
        if notification_id:
            archive_notification(client, space_id, notification_id)
        else:
            log.warning("Could not find notification ID to archive")
        log.info("Backup completed successfully")
    except Exception:
        log.exception("Backup failed")
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
