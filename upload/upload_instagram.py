import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def upload_to_instagram(video_path, caption=""):
    print("\n" + "=" * 60)
    print("INSTAGRAM REEL UPLOAD STARTING")
    print("=" * 60)

    access_token = (
        os.getenv('IG_ACCESS_TOKEN') or
        os.getenv('INSTAGRAM_ACCESS_TOKEN') or
        os.getenv('FB_ACCESS_TOKEN_1') or
        os.getenv('FACEBOOK_ACCESS_TOKEN')
    )
    user_id = os.getenv('IG_ACCOUNT_ID') or os.getenv('INSTAGRAM_ACCOUNT_ID')

    if not access_token:
        print("[instagram] Skipping - missing access token")
        return {'status': 'skipped', 'reason': 'Missing access token'}

    if not user_id:
        print("[instagram] Skipping - missing Instagram Account ID")
        return {'status': 'skipped', 'reason': 'Missing account ID'}

    video_path_obj = Path(video_path)
    if not video_path_obj.exists():
        print(f"[instagram] Video file not found: {video_path}")
        return {'status': 'failed', 'error': 'Video file not found'}

    file_size = video_path_obj.stat().st_size
    api_base = "https://graph.facebook.com/v21.0"

    try:
        # Step 1: Create Resumable Reel Container
        print(f"[instagram] Step 1: Creating resumable Reel container for IG User {user_id}...")
        c_params = {
            'media_type': 'REELS',
            'upload_type': 'resumable',
            'caption': caption[:2200] if caption else '',
            'access_token': access_token,
            'share_to_feed': False
        }

        c_res = requests.post(f"{api_base}/{user_id}/media", params=c_params, timeout=30)
        if c_res.status_code not in (200, 201):
            err = c_res.json().get('error', {}).get('message', c_res.text)
            raise Exception(f"Container creation failed: {err}")

        c_data = c_res.json()
        container_id = c_data.get('id')
        upload_uri = c_data.get('uri')
        print(f"[instagram] Container ID created: {container_id}")

        # Step 2: Upload bytes
        print("[instagram] Step 2: Uploading video bytes to Meta...")
        with open(video_path_obj, 'rb') as f:
            video_bytes = f.read()

        up_headers = {
            'Authorization': f'OAuth {access_token}',
            'offset': '0',
            'file_size': str(file_size)
        }
        up_res = requests.post(upload_uri, headers=up_headers, data=video_bytes, timeout=120)
        if up_res.status_code not in (200, 201):
            raise Exception(f"Video upload failed: {up_res.text}")

        print("[instagram] Video bytes successfully received.")

        # Step 3: Wait for container processing
        print("[instagram] Step 3: Polling container processing status...")
        max_attempts = 30
        status_url = f"{api_base}/{container_id}"
        is_ready = False

        for attempt in range(max_attempts):
            time.sleep(5)
            s_res = requests.get(status_url, params={'fields': 'status_code,status', 'access_token': access_token}, timeout=20)
            if s_res.status_code == 200:
                s_data = s_res.json()
                code = s_data.get('status_code')
                print(f"[instagram] Status check ({attempt + 1}/{max_attempts}): {code}")
                if code == 'FINISHED':
                    is_ready = True
                    break
                elif code == 'ERROR':
                    raise Exception(f"Meta container error: {s_data.get('status', 'Unknown error')}")

        if not is_ready:
            raise TimeoutError("Timed out waiting for Instagram to process the video")

        # Step 4: Publish container
        print("[instagram] Step 4: Publishing container to feed...")
        pub_url = f"{api_base}/{user_id}/media_publish"
        pub_res = requests.post(pub_url, params={'creation_id': container_id, 'access_token': access_token}, timeout=30)
        
        if pub_res.status_code not in (200, 201):
            err = pub_res.json().get('error', {}).get('message', pub_res.text)
            raise Exception(f"Publish failed: {err}")

        pub_data = pub_res.json()
        media_id = pub_data.get('id')
        print(f"[instagram] Reel successfully published! Media ID: {media_id}")
        return {'status': 'success', 'media_id': media_id}

    except Exception as e:
        print(f"[instagram] Error: {e}")
        return {'status': 'failed', 'error': str(e)}
