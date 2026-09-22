import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def upload_reel_to_page(video_path, description, title, page_id, access_token):
    if not access_token or not page_id:
        print(f"[facebook] Missing page_id or access_token for page {page_id}")
        return {"status": "skipped", "reason": "Missing credentials"}

    video_path_obj = Path(video_path)
    if not video_path_obj.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    file_size = video_path_obj.stat().st_size
    print(f"[facebook] Uploading to Page {page_id} (Size: {file_size / (1024 * 1024):.2f} MB)...")

    # Step 1: Start upload session
    start_url = f"https://graph.facebook.com/v21.0/{page_id}/video_reels"
    start_data = {
        'access_token': access_token,
        'upload_phase': 'start',
        'file_size': file_size
    }
    res_start = requests.post(start_url, data=start_data, timeout=30)
    if res_start.status_code != 200:
        print(f"[facebook] Error initializing reel upload: {res_start.text}")
        return {"status": "failed", "error": res_start.text}

    start_json = res_start.json()
    video_id = start_json.get('video_id')
    upload_url = start_json.get('upload_url')

    # Step 2: Upload binary bytes
    with open(video_path_obj, 'rb') as f:
        video_data = f.read()

    headers = {
        'Authorization': f'OAuth {access_token}',
        'offset': '0',
        'file_size': str(file_size)
    }
    res_upload = requests.post(upload_url, headers=headers, data=video_data, timeout=120)
    if res_upload.status_code not in (200, 201):
        print(f"[facebook] Error transferring bytes: {res_upload.text}")
        return {"status": "failed", "error": res_upload.text}

    # Step 3: Finish and publish
    finish_data = {
        'access_token': access_token,
        'upload_phase': 'finish',
        'video_id': video_id,
        'video_state': 'PUBLISHED',
        'description': description,
        'title': title
    }
    res_finish = requests.post(start_url, data=finish_data, timeout=30)
    if res_finish.status_code != 200:
        print(f"[facebook] Error finishing upload: {res_finish.text}")
        return {"status": "failed", "error": res_finish.text}

    print(f"[facebook] Reel successfully published to Page {page_id}! Video ID: {video_id}")
    return {"status": "success", "video_id": video_id, "page_id": page_id}


def upload_to_facebook_pages(video_path, description, title):
    print("\n" + "=" * 60)
    print("FACEBOOK UPLOAD STARTING")
    print("=" * 60)

    results = []

    # Page 1: kreggscode
    page1_id = os.getenv("FB_PAGE_ID_1") or os.getenv("FACEBOOK_PAGE_ID")
    page1_token = os.getenv("FB_ACCESS_TOKEN_1") or os.getenv("FACEBOOK_ACCESS_TOKEN")
    if page1_id and page1_token:
        print(f"\n[facebook] Uploading to Page 1: {page1_id}")
        try:
            r1 = upload_reel_to_page(video_path, description, title, page1_id, page1_token)
            results.append(r1)
        except Exception as e:
            print(f"[facebook] Failed upload to Page 1: {e}")
            results.append({"status": "failed", "error": str(e), "page_id": page1_id})

    # Page 2: kreggscode coding
    page2_id = os.getenv("FB_PAGE_ID_2")
    page2_token = os.getenv("FB_ACCESS_TOKEN_2")
    if page2_id and page2_token:
        print(f"\n[facebook] Uploading to Page 2: {page2_id}")
        try:
            r2 = upload_reel_to_page(video_path, description, title, page2_id, page2_token)
            results.append(r2)
        except Exception as e:
            print(f"[facebook] Failed upload to Page 2: {e}")
            results.append({"status": "failed", "error": str(e), "page_id": page2_id})

    if not results:
        print("[facebook] No Facebook credentials configured")
        return {"status": "skipped", "reason": "No credentials"}

    return results
