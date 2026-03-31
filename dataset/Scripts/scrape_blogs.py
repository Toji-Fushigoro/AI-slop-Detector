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
        # Check if text is English
        return detect(text) == "en"
    except:
        return False


def get_devto_links(tag):
    url = f"https://dev.to/t/{tag}/latest"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.content, "lxml")
        links = []
        for a in soup.find_all(
            "a", class_="crayons-story__hidden-navigation-link", href=True
        ):
            href = a["href"]
            if href.startswith("http"):
                links.append(href)
            else:
                links.append(f"https://dev.to{href}")
        return links
    except Exception as e:
        print(f"Error fetching links for {tag}: {e}")
        return []


def scrape_article(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.content, "lxml")
        title_tag = soup.find("h1")
        if not title_tag:
            return None
        title = title_tag.get_text().strip()

        # Check if title is English
        if not is_english(title) and len(title) > 10:
            # We'll also check paragraphs below, but title is a good hint
            pass

        article_body = soup.find("div", id="article-body") or soup.find(
            "div", class_="crayons-article__main"
        )
        if not article_body:
            return None

        paragraphs = []
        for p in article_body.find_all("p"):
            text = p.get_text().strip()
            if len(text) > 100:  # Ensure substantive paragraphs
                if is_english(text):
                    paragraphs.append(text)
            if len(paragraphs) >= 5:
                break

        if len(paragraphs) < 3:
            return None

        return {
            "title": title,
            "url": url,
            "content": "\n\n".join(paragraphs),
        }
    except Exception as e:
        print(f"Error scraping article {url}: {e}")
        return None


def main():
    tags = ["ai", "history", "mythology"]
    dataset = []

    # Ensure dataset directory exists
    os.makedirs("dataset", exist_ok=True)

    print("Starting Blog scrape (Dev.to)...")
    for tag in tags:
        if len(dataset) >= 15:
            break

        links = get_devto_links(tag)
        for link in links:
            if len(dataset) >= 15:
                break

            # Check if link is already in dataset
            if any(item["url"] == link for item in dataset):
                continue

            data = scrape_article(link)
            if data and data["content"]:
                dataset.append(
                    {
                        "source": "Dev.to",
                        "title": data["title"],
                        "url": data["url"],
                        "content": data["content"],
                    }
                )
                print(f"Scraped ({len(dataset)}/15): {data['title']}")
                time.sleep(2)  # Stricter delay for blogs

    output_path = os.path.join("dataset", "raw_blogs.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=4, ensure_ascii=False)
    print(f"Blog scrape complete. Saved to {output_path}")


if __name__ == "__main__":
    main()
