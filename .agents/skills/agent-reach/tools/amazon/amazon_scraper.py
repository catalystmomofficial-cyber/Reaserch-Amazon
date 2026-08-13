import os
import sys
import json
import urllib.parse
import requests

def get_token():
    token = os.environ.get("SCRAPEDO_API_TOKEN")
    if not token:
        print(json.dumps({
            "status": "error",
            "errorMessage": "Missing SCRAPEDO_API_TOKEN environment variable. Please set it before running this scraper."
        }, indent=2))
        sys.exit(1)
    return token

def search_amazon(keyword, geocode="us", page=1):
    token = get_token()
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://api.scrape.do/plugin/amazon/search?token={token}&keyword={encoded_keyword}&geocode={geocode.lower()}&page={page}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {
            "status": "error",
            "errorMessage": f"Request failed: {str(e)}"
        }

def get_pdp(asin, geocode="us"):
    token = get_token()
    url = f"https://api.scrape.do/plugin/amazon/pdp?token={token}&asin={asin}&geocode={geocode.lower()}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {
            "status": "error",
            "errorMessage": f"Request failed: {str(e)}"
        }

def get_offers(asin, geocode="us"):
    token = get_token()
    url = f"https://api.scrape.do/plugin/amazon/offer-listing?token={token}&asin={asin}&geocode={geocode.lower()}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {
            "status": "error",
            "errorMessage": f"Request failed: {str(e)}"
        }

def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python3 amazon_scraper.py search <keyword> [geocode=us] [page=1]")
        print("  python3 amazon_scraper.py pdp <asin> [geocode=us]")
        print("  python3 amazon_scraper.py offers <asin> [geocode=us]")
        sys.exit(1)

    command = sys.argv[1].lower()
    arg = sys.argv[2]

    if command == "search":
        geocode = sys.argv[3] if len(sys.argv) > 3 else "us"
        page = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        result = search_amazon(arg, geocode, page)
    elif command == "pdp":
        geocode = sys.argv[3] if len(sys.argv) > 3 else "us"
        result = get_pdp(arg, geocode)
    elif command == "offers":
        geocode = sys.argv[3] if len(sys.argv) > 3 else "us"
        result = get_offers(arg, geocode)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
