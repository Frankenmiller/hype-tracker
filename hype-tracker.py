import os
import json
import xml.etree.ElementTree as ET
import requests
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. Initialization
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Missing GEMINI_API_KEY in .env file.")

client = genai.Client(api_key=api_key)
STORAGE_FILE = "tracked_hype.json"

# 2. Fetch data stream
def fetch_raw_data():
    print("🔄 Fetching latest data stream...")
    url = "https://news.ycombinator.com/rss"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch data. Status: {response.status_code}")
        return []
        
    root = ET.fromstring(response.content)
    items = []
    for item in root.findall(".//item")[:20]: # Bumped to 20 to catch more potential hits
        items.append({
            "title": item.find("title").text,
            "link": item.find("link").text
        })
    return items

# 3. Agent filtering and reasoning
def analyze_with_agent(raw_items):
    print("🤖 Agent analyzing current batch...")
    
    system_instruction = (
        "You are an elite developer screening agent. Analyze the incoming text list. "
        "Filter and preserve ONLY items explicitly focusing on: AI agents, LLM pipelines, "
        "automation logic, Python scripts, or Rust programming applications. "
        "Ignore standard generic tech news, funding announcements, or opinion essays. "
        "Format response strictly as a JSON list of objects containing 'title', 'url', and 'reason'."
    )
    
    prompt = f"Filter this stream:\n{json.dumps(raw_items)}"
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.1
        ),
    )
    
    try:
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ JSON parsing breakdown: {e}")
        return []

# 4. Load past state, cross-reference, and merge unique findings
def process_and_save_archive(new_discoveries):
    # Load existing memory archive if it exists
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r") as f:
                archive = json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Archive file was corrupted or empty. Resetting memory structure.")
            archive = []
    else:
        archive = []

    # Map existing URLs to prevent duplicates
    existing_urls = {item["url"] for item in archive}
    
    added_count = 0
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item in new_discoveries:
        if item["url"] not in existing_urls:
            # Inject meta-data state tracking
            item["discovered_at"] = timestamp
            archive.append(item)
            added_count += 1
            print(f"✨ New Target Captured: {item['title'][:50]}...")

    if added_count > 0:
        with open(STORAGE_FILE, "w") as f:
            json.dump(archive, f, indent=4)
        print(f"💾 Saved {added_count} brand new unique findings to permanent archive storage.")
    else:
        print("⏸️ Check complete. No fresh targets found in this stream interval.")

# Main Pipeline Loop
if __name__ == "__main__":
    current_stream = fetch_raw_data()
    if current_stream:
        agent_picks = analyze_with_agent(current_stream)
        process_and_save_archive(agent_picks)