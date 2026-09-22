import os
import re
import json
import random
import requests
from dotenv import load_dotenv

load_dotenv()

POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "openai")


def clean_filename(filename):
    base = os.path.splitext(filename)[0]
    cleaned = re.sub(r'[-_]+', ' ', base)
    cleaned = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)
    cleaned = ' '.join(cleaned.split())
    return cleaned


def generate_metadata_from_filename(filename):
    clean_topic = clean_filename(filename)
    print(f"[caption] Extracted topic from filename: '{clean_topic}'")

    default_tags = [
        "coding", "programming", "computerscience", "developer",
        "softwareengineering", "tech", "algorithms", "learncoding",
        "code", "kreggscode", "python"
    ]

    fallback_title = f"{clean_topic} Explained #Shorts"
    fallback_desc = (
        f"{clean_topic} explained step by step.\n\n"
        f"Understanding the core principles of computer science and software development "
        f"helps you write cleaner, faster, and more scalable code.\n\n"
        f"Save this for your next coding interview and follow @kreggscode for more daily engineering concepts!\n\n"
        f"#coding #programming #computerscience #softwareengineering #developer #tech #kreggscode #Shorts"
    )

    if not POLLINATIONS_API_KEY:
        print("[caption] POLLINATIONS_API_KEY not found. Using fallback metadata.")
        return fallback_title, fallback_desc, default_tags

    prompt = (
        f"You are a social media tech content creator for 'kreggscode', a popular channel teaching "
        f"computer science, coding, system architecture, and software engineering in concise, engaging animations.\n\n"
        f"The video topic extracted from the file name is: '{clean_topic}'\n\n"
        f"Please generate:\n"
        f"1. A catchy, high-CTR Title (maximum 90 characters, punchy, curiosity-inducing, ending with #Shorts).\n"
        f"2. A compelling Description (3 to 5 engaging sentences explaining why this concept matters in computer science or programming, "
        f"with a hook, clear explanation, and a call-to-action to follow @kreggscode and drop questions in comments).\n"
        f"3. 10-15 relevant lowercase hashtags/tags without the '#' prefix for metadata.\n\n"
        f"Return ONLY a valid JSON object matching this schema without any markdown formatting:\n"
        f'{{"title": "...", "description": "...", "tags": ["tag1", "tag2", ...]}}'
    )

    url = "https://gen.pollinations.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {POLLINATIONS_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": AI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        raw_content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        cleaned_json = raw_content.replace('```json', '').replace('```', '').strip()
        parsed = json.loads(cleaned_json)

        title = parsed.get("title", fallback_title).strip()
        description = parsed.get("description", fallback_desc).strip()
        tags = parsed.get("tags", default_tags)
        if isinstance(tags, list):
            tags = [str(t).replace("#", "").strip() for t in tags if t]
        else:
            tags = default_tags

        if "#Shorts" not in title:
            title = f"{title} #Shorts"

        return title, description, tags

    except Exception as e:
        print(f"[caption] AI Generation failed ({e}). Using generated fallback.")
        return fallback_title, fallback_desc, default_tags
