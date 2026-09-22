import os
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

load_dotenv()


def get_authenticated_service():
    client_id = (os.getenv('YT_CLIENT_ID') or os.getenv('YOUTUBE_CLIENT_ID', '')).strip()
    client_secret = (os.getenv('YT_CLIENT_SECRET') or os.getenv('YOUTUBE_CLIENT_SECRET', '')).strip()
    refresh_token = (os.getenv('YT_REFRESH_TOKEN') or os.getenv('YOUTUBE_REFRESH_TOKEN', '')).strip()

    if not all([client_id, client_secret, refresh_token]):
        print("[youtube] Missing YouTube credentials. Skipping YouTube upload.")
        return None

    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/youtube"]
    )

    try:
        creds.refresh(Request())
    except Exception as e:
        print(f"[youtube] Refresh token failed: {e}")
        return None

    return build('youtube', 'v3', credentials=creds)


def upload_to_youtube(video_path, title, description, tags=None, category_id='27'):
    print("\n" + "=" * 60)
    print("YOUTUBE SHORTS UPLOAD STARTING")
    print("=" * 60)

    youtube = get_authenticated_service()
    if not youtube:
        return {'status': 'skipped', 'reason': 'Missing or invalid YouTube credentials'}

    if not tags:
        tags = ['coding', 'computerscience', 'programming', 'developer', 'softwareengineering']

    video_path_obj = Path(video_path)
    if not video_path_obj.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Ensure #Shorts is present in title and description
    if '#Shorts' not in description:
        description = f"{description}\n\n#Shorts"

    body = {
        'snippet': {
            'title': title[:100],
            'description': description,
            'tags': tags,
            'categoryId': category_id  # 27 is Education
        },
        'status': {
            'privacyStatus': 'public',
            'selfDeclaredMadeForKids': False
        }
    }

    media = MediaFileUpload(
        str(video_path_obj),
        chunksize=1024 * 1024 * 4,
        resumable=True,
        mimetype='video/mp4'
    )

    print(f"[youtube] Uploading: {title}")
    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"[youtube] Progress: {int(status.progress() * 100)}%")

    video_id = response.get('id')
    print(f"[youtube] Video successfully uploaded! ID: {video_id}")
    print(f"[youtube] URL: https://youtube.com/shorts/{video_id}")
    return {'status': 'success', 'video_id': video_id}
