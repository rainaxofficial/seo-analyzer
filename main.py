from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route("/analyze", methods=["GET"])
def analyze():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "URL is required"}), 400

    if not url.startswith("http"):
        url = "http://" + url

    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        title = soup.title.string.strip() if soup.title else ""
        desc = ""
        canonical = ""
        viewport = ""
        og = {}
        twitter = {}
        schema = soup.find_all("script", type="application/ld+json")

        for tag in soup.find_all("meta"):
            name = tag.get("name", "").lower()
            prop = tag.get("property", "").lower()
            if name == "description":
                desc = tag.get("content", "")
            if name == "viewport":
                viewport = tag.get("content", "")
            if prop.startswith("og:"):
                og[prop] = tag.get("content", "")
            if name.startswith("twitter:"):
                twitter[name] = tag.get("content", "")

        canonical_tag = soup.find("link", rel="canonical")
        if canonical_tag:
            canonical = canonical_tag.get("href", "")

        h1 = [h.get_text(strip=True) for h in soup.find_all("h1")]
        h2 = [h.get_text(strip=True) for h in soup.find_all("h2")]
        h3 = [h.get_text(strip=True) for h in soup.find_all("h3")]

        imgs = soup.find_all("img")
        missing_alt = sum(1 for img in imgs if not img.get("alt"))

        text = soup.get_text(" ", strip=True)
        words = re.findall(r"\b\w+\b", text.lower())
        word_count = len(words)

        keyword_freq = {}
        for word in words:
            if len(word) > 3:
                keyword_freq[word] = keyword_freq.get(word, 0) + 1
        keyword_density = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:20]

        links = soup.find_all("a", href=True)
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        internal = []
        external = []
        for link in links:
            href = link["href"]
            if href.startswith("/") or domain in href:
                internal.append(href)
            else:
                external.append(href)

        # Check robots.txt & sitemap.xml
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        robots_status = requests.get(base_url + "/robots.txt").status_code == 200
        sitemap_status = requests.get(base_url + "/sitemap.xml").status_code == 200

        return jsonify({
            "title": title,
            "description": desc,
            "canonical": canonical,
            "viewport": viewport,
            "h1": h1,
            "h2": h2,
            "h3": h3,
            "word_count": word_count,
            "missing_alt": missing_alt,
            "keywords": keyword_density,
            "internal_links": internal,
            "external_links": external,
            "robots_txt": robots_status,
            "sitemap_xml": sitemap_status,
            "og": og,
            "twitter": twitter,
            "schema_count": len(schema)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
