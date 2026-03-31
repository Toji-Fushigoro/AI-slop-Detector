import requests
from bs4 import BeautifulSoup
import json
import time
import os
from langdetect import detect, DetectorFactory

# Ensure reproducible results
DetectorFactory.seed = 0


def is_english(text):
    try:
        return detect(text) == "en"
    except:
        return False


def get_wiki_content(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Failed to fetch {url}: Status {response.status_code}")
            return None

        soup = BeautifulSoup(response.content, "lxml")
        title_tag = soup.find("h1", id="firstHeading")
        if not title_tag:
            return None
        title = title_tag.text

        content_div = soup.find("div", id="mw-content-text").find(
            "div", class_="mw-parser-output"
        )
        paragraphs = []
        links = []

        if content_div:
            # First, check if the article title is in English or common enough
            if not is_english(title) and len(title) > 10:
                # If title is short or hard to detect, we'll check paragraphs
                pass

            for p in content_div.find_all("p", recursive=False):
                text = p.get_text().strip()
                if text and len(text) > 50:
                    # Check if paragraph is English
                    if is_english(text):
                        paragraphs.append(text)
                if len(paragraphs) >= 3:
                    break

            # If we couldn't find 3 English paragraphs, skip this page
            if len(paragraphs) < 3:
                return None

            # Collect links from these paragraphs for recursion
            for p in content_div.find_all("p", limit=20):
                for a in p.find_all("a", href=True):
                    link = a["href"]
                    if link.startswith("/wiki/") and ":" not in link:
                        links.append(f"https://en.wikipedia.org{link}")

        return {
            "title": title,
            "url": url,
            "paragraphs": paragraphs[:3],
            "links": list(set(links)),
        }
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None


def main():
    seeds = [
        "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "https://en.wikipedia.org/wiki/History",
        "https://en.wikipedia.org/wiki/Mythology",
    ]

    dataset = []
    visited = set()
    queue = seeds.copy()

    # Ensure dataset directory exists
    os.makedirs("dataset", exist_ok=True)

    print("Starting Wikipedia scrape...")
    while len(dataset) < 15 and queue:
        current_url = queue.pop(0)
        if current_url in visited:
            continue

        visited.add(current_url)
        data = get_wiki_content(current_url)

        if data and len(data["paragraphs"]) >= 3:
            dataset.append(
                {
                    "source": "Wikipedia",
                    "title": data["title"],
                    "url": data["url"],
                    "content": "\n\n".join(data["paragraphs"]),
                }
            )
            print(f"Scraped ({len(dataset)}/15): {data['title']}")

            # Add new links to queue to ensure we reach 15
            for link in data["links"]:
                if link not in visited:
                    queue.append(link)

        # Slightly longer delay to be extra respectful and avoid hitting rate limits
        time.sleep(1.5)

    output_path = os.path.join("dataset", "raw_wikipedia.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=4, ensure_ascii=False)
    print(f"Wikipedia scrape complete. Saved to {output_path}")


if __name__ == "__main__":
    main()
