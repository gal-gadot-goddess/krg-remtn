import os
import json
import io
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "1ErzyEzHpqLlG5y_egk_0JitF0oFVAGUI")
GOOGLE_SERVICE_ACCOUNT_KEY = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "downloads")
PUBLISHED_LOG = "published_videos.json"


def get_published_videos():
    if os.path.exists(PUBLISHED_LOG):
        try:
            with open(PUBLISHED_LOG, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [item.get('video_name', '') for item in data if isinstance(item, dict)]
        except Exception:
            return []
    return []


def get_drive_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    scopes = ['https://www.googleapis.com/auth/drive']

    if not GOOGLE_SERVICE_ACCOUNT_KEY:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_KEY environment variable is not set")

    if os.path.exists(GOOGLE_SERVICE_ACCOUNT_KEY):
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_KEY, scopes=scopes
        )
    elif GOOGLE_SERVICE_ACCOUNT_KEY.strip().startswith('{'):
        info = json.loads(GOOGLE_SERVICE_ACCOUNT_KEY)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=scopes
        )
    else:
        raise ValueError("Invalid GOOGLE_SERVICE_ACCOUNT_KEY value")

    return build('drive', 'v3', credentials=creds)


def fetch_one_video_from_drive(allow_repost=False):
    service = get_drive_service()
    if not service:
        print("[drive] Failed to initialize Google Drive service")
        return None

    query = f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and trashed = false and mimeType contains 'video/'"
    results = service.files().list(
        q=query,
        pageSize=100,
        fields="nextPageToken, files(id, name, mimeType, size)",
        orderBy="createdTime desc"
    ).execute()

    files = results.get('files', [])
    if not files:
        print("[drive] No video files found in Google Drive folder")
        return None

    published_names = set(get_published_videos())
    available = [f for f in files if f['name'] not in published_names]

    target_file = None
    if available:
        target_file = available[0]
        print(f"[drive] Found {len(available)} new video(s). Selecting: {target_file['name']}")
    elif allow_repost and files:
        target_file = files[0]
        print(f"[drive] All videos published. Reposting: {target_file['name']}")
    else:
        print("[drive] All videos in Google Drive have already been published")
        return None

    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    destination = os.path.join(DOWNLOADS_DIR, target_file['name'])

    print(f"[drive] Downloading {target_file['name']} ({target_file['id']})...")
    from googleapiclient.http import MediaIoBaseDownload
    request = service.files().get_media(fileId=target_file['id'])
    
    with open(destination, 'wb') as fh:
        downloader = MediaIoBaseDownload(fh, request, chunksize=1024 * 1024 * 4)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"[drive] Download progress: {int(status.progress() * 100)}%")

    print(f"[drive] Download complete: {destination}")
    return destination, target_file['name'], target_file['id']
