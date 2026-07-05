import os
import json
import time
import sys
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape
import xml.etree.ElementTree as ET
import requests
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# 1. Initialization
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Missing GEMINI_API_KEY in .env file.")

client = genai.Client(api_key=api_key)
STORAGE_FILE = "tracked_hype.json"

# Pydantic Schemas to guarantee rigid JSON formatting from the AI
class DiscoveryItem(BaseModel):
    title: str
    url: str = Field(description="The source URL or link of the article")
    reason: str = Field(description="Brief explanation of why this matches the criteria")

class DiscoveryList(BaseModel):
    items: list[DiscoveryItem]

def dramatic_pause(dots=5, delay=0.5):
    for _ in range(dots):
        print(".", end="", flush=True)
        time.sleep(delay)
    print()

# 2. Fetch data stream
def fetch_raw_data():
    print("\n🔄 Fetching latest data stream ", end="")
    dramatic_pause(5, 0.4)
    print()
    url = "https://news.ycombinator.com/rss"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Failed to fetch data. Error: {e}")
        return []
        
    root = ET.fromstring(response.content)
    items = []
    for item in root.findall(".//item")[:30]: # Bumped to 30 to catch a wider net
        title_el = item.find("title")
        link_el = item.find("link")
        if title_el is None or link_el is None:
            continue
        items.append({"title": title_el.text, "url": link_el.text})
    return items

# 3. Agent filtering and reasoning
def analyze_with_agent(raw_items): ##-------------------> analyze_with_agent
    print("🤖 Agent analyzing current batch ", end="")
    dramatic_pause(5, 0.4)
    print()
    
    print(f"DEBUG: Passing {len(raw_items)} items to Gemini.")
    
    system_instruction = (
        "You are an elite developer screening agent filtering a live Hacker News feed. "
        "Your goal is to find technical projects, tools, frameworks, libraries, or articles "
        "related to: AI agents, LLMs, machine learning pipelines, automation, or programming "
        "ecosystems like Python and Rust.\n\n"
        "Be permissive: if a title implies a software library, developer tool, or programmable automation "
        "built in these ecosystems, preserve it. Ignore completely unrelated general tech news."
    )
    
    prompt = f"Filter this stream:\n{json.dumps(raw_items)}"
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=DiscoveryList,
                temperature=0.1
            ),
        )
        
        print(f"DEBUG: Raw Agent Response: {response.text}")
        
        structured_data = json.loads(response.text)
        return structured_data.get("items", [])
        
    except Exception as e:
        print(f"❌ API or Parsing breakdown: {e}")
        return []

# 4. Load past state, cross-reference, and merge unique findings
def process_and_save_archive(new_discoveries):
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r") as f:
                archive = json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Archive file was corrupted or empty. Resetting memory structure.")
            archive = []
    else:
        archive = []

    existing_urls = {item["url"] for item in archive if isinstance(item, dict) and "url" in item}
    
    added_count = 0
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item in new_discoveries:
        # Normalize Pydantic objects or dicts cleanly before serialization
        item_dict = item if isinstance(item, dict) else item.model_dump()
        
        if item_dict["url"] not in existing_urls:
            item_dict["discovered_at"] = timestamp
            archive.append(item_dict)
            added_count += 1
            print(f"✨ New Target Captured: {item_dict['title'][:50]}...")

    if added_count > 0:
        with open(STORAGE_FILE, "w") as f:
            json.dump(archive, f, indent=4)
        print(f"💾 Saved {added_count} brand new unique findings to permanent archive storage.")
    else:
        print("⏸️ Check complete. No fresh targets found in this stream interval.")

def generate_html_dashboard(archive_data, output_dir="docs"):
    print(f"🎨 Compiling HTML dashboard...")
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Sort the data
    sorted_archive = sorted(archive_data, key=lambda x: x.get("discovered_at", ""), reverse=True)
    
    # 2. Set up Jinja2 to load templates from the current directory ('.')
    # If you put your template in a folder named 'templates', change '.' to 'templates'
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('template.html')
    
    # 3. Render the HTML by passing your variables into the template
    rendered_html = template.render(
        sorted_archive=sorted_archive,
        compiled_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    # 4. Save the file (Now safely outside the loop)
    output_path = os.path.join(output_dir, "index.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)
        
    print(f"✅ Dashboard written to {output_path}")

# Main Pipeline Loop
if __name__ == "__main__":
    current_stream = fetch_raw_data()
    if current_stream:
        agent_picks = analyze_with_agent(current_stream)
        process_and_save_archive(agent_picks)
    
    # Always regenerate the dashboard from current archive state,
    # even on runs with zero new discoveries
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            archive = json.load(f)
        generate_html_dashboard(archive)