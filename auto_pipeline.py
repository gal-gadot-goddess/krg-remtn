import os
import sys
import json
import datetime
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

from google_drive_fetch import fetch_one_video_from_drive, PUBLISHED_LOG
from caption_generator import generate_metadata_from_filename
from upload.upload_facebook import upload_to_facebook_pages
from upload.upload_instagram import upload_to_instagram
from upload.upload_to_youtube import upload_to_youtube


def mark_as_published(video_name, metadata):
    published = []
    if os.path.exists(PUBLISHED_LOG):
        try:
            with open(PUBLISHED_LOG, 'r', encoding='utf-8') as f:
                published = json.load(f)
        except Exception:
            published = []

    published.append({
        "video_name": video_name,
        "published_at": datetime.datetime.utcnow().isoformat(),
        "metadata": metadata
    })

    with open(PUBLISHED_LOG, 'w', encoding='utf-8') as f:
        json.dump(published, f, indent=2)


def run_pipeline():
    print("\n" + "=" * 60)
    print("STARTING KRG-REMTN AUTOMATION PIPELINE")
    print("=" * 60 + "\n")

    # Step 1: Fetch video from Google Drive
    print("STEP 1: Fetching video from Google Drive...")
    fetch_result = fetch_one_video_from_drive(allow_repost=False)

    if not fetch_result:
        print("[pipeline] No new videos found. Attempting repost mode...")
        fetch_result = fetch_one_video_from_drive(allow_repost=True)

    if not fetch_result:
        print("[pipeline] No videos available to publish. Pipeline ending gracefully.")
        return

    video_path, video_name, file_id = fetch_result
    print(f"[pipeline] Successfully retrieved video: {video_name}")

    # Step 2: Extract filename & generate AI caption/title/tags
    print("\nSTEP 2: Generating title, description, and tags from filename...")
    title, description, tags = generate_metadata_from_filename(video_name)

    print(f"\n[pipeline] Generated Title: {title}")
    print(f"[pipeline] Generated Description:\n{description}")
    print(f"[pipeline] Generated Tags: {', '.join(tags)}\n")

    results = {
        "facebook": None,
        "instagram": None,
        "youtube": None
    }

    # Step 3: Publish to Facebook Pages
    print("STEP 3A: Uploading to Facebook Pages...")
    try:
        results["facebook"] = upload_to_facebook_pages(video_path, description, title)
    except Exception as e:
        print(f"[pipeline] Facebook error: {e}")
        results["facebook"] = {"status": "failed", "error": str(e)}

    # Step 4: Publish to Instagram Reels
    print("\nSTEP 3B: Uploading to Instagram Reels...")
    try:
        combined_caption = f"{title}\n\n{description}"
        results["instagram"] = upload_to_instagram(video_path, combined_caption)
    except Exception as e:
        print(f"[pipeline] Instagram error: {e}")
        results["instagram"] = {"status": "failed", "error": str(e)}

    # Step 5: Publish to YouTube Shorts
    print("\nSTEP 3C: Uploading to YouTube Shorts...")
    try:
        results["youtube"] = upload_to_youtube(video_path, title, description, tags)
    except Exception as e:
        print(f"[pipeline] YouTube error: {e}")
        results["youtube"] = {"status": "failed", "error": str(e)}

    # Step 6: Log published video
    print("\nSTEP 4: Updating published videos record...")
    mark_as_published(video_name, {
        "title": title,
        "description": description,
        "tags": tags,
        "results": results
    })

    # Step 7: Clean up local file
    try:
        if os.path.exists(video_path):
            os.remove(video_path)
            print(f"[pipeline] Cleaned up temporary video file: {video_path}")
    except Exception as e:
        print(f"[pipeline] Notice: Could not remove temporary file: {e}")

    print("\n" + "=" * 60)
    print("KRG-REMTN AUTOMATION PIPELINE COMPLETED")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_pipeline()
