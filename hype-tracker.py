import os
import json
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Missing GEMINI_API_KEY in .env file. Check your .env setup!")

client = genai.Client(api_key=api_key)

def fetch_raw_data():
    print("🔄 Fetching latest data stream...")
    url = "https://news.ycombinator.com/rss"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch data. Status: {response.status_code}")
        return []
        
    # Parse the XML RSS feed
    root = ET.fromstring(response.content)
    items = []
    for item in root.findall(".//item")[:15]:  # Just grab the top 15 items to keep it light
        items.append({
            "title": item.find("title").text,
            "link": item.find("link").text
        })
    return items

def analyze_with_agent(raw_items):
    print("🤖 Agent is analyzing items for high-value targets...")
    
    # We define exactly what we want the AI to look for
    system_instruction = (
        "You are a scanning agent. Filter the incoming list of tech articles. "
        "Only keep items that mention or heavily relate to: AI, Agents, Automation, Python, or Rust. "
        "Ignore everything else. You must return the data strictly as a JSON list of objects, "
        "where each object has 'title', 'url', and a short 1-sentence 'reason' why it passed the filter."
    )
    
    prompt = f"Analyze these items:\n{json.dumps(raw_items)}"
    
    # We enforce a strict JSON output structure from the model
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.1 # Low temperature means more predictable, precise execution
        ),
    )
    
    try:
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ Error parsing agent JSON response: {e}")
        return []
    
def save_results(analyzed_data):
    filename = "tracked_hype.json"
    print(f"💾 Saving filtered results to {filename}...")
    with open(filename, "w") as f:
        json.dump(analyzed_data, f, indent=4)
    print("✅ Done!")

# Main Execution Loop
if __name__ == "__main__":
    raw_data = fetch_raw_data()
    if raw_data:
        filtered_data = analyze_with_agent(raw_data)
        save_results(filtered_data)    