import os
import sys
import json
import requests

# Import Scrape.do Amazon Scraper helper dynamically using canonical .agents path
import importlib.util
spec = importlib.util.spec_from_file_location(
    "amazon_scraper", "/app/.agents/skills/agent-reach/tools/amazon/amazon_scraper.py"
)
amazon_scraper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(amazon_scraper)

def run_integration_pipeline(keyword, geocode="us"):
    print(f"--- Running Real Executable Proof-of-Concept Integration Pipeline ---")
    print(f"Keyword: '{keyword}', Market: {geocode.upper()}\n")

    # Guard check for Scrape.do API token to run real API calls vs. Mock gracefully
    token_set = bool(os.environ.get("SCRAPEDO_API_TOKEN"))

    # 1. Search Amazon for the product keyword
    print("[Step 1] Searching Amazon via Scrape.do structured endpoint...")
    if token_set:
        search_results = amazon_scraper.search_amazon(keyword, geocode)
    else:
        print(" -> [Notice] SCRAPEDO_API_TOKEN missing. Failing gracefully but outputting schema layout for guidance.")
        search_results = {
            "keyword": keyword,
            "page": 1,
            "products": [
                {
                    "asin": "B0C7BKZ883",
                    "title": "Adjustable Laptop Stand for Desk, Metal Foldable Laptop Riser Holder",
                    "url": "https://www.amazon.com/dp/B0C7BKZ883",
                    "imageUrl": "https://m.media-amazon.com/images/I/71Jz2L1pV6L._AC_SX679_.jpg",
                    "price": {"currencyCode": "USD", "amount": 14.99},
                    "rating": {"value": 4.6, "count": 2712, "stars": 5},
                    "reviewCount": "(2.7K)",
                    "isSponsored": False,
                    "isPrime": True,
                    "position": 1,
                    "badge": "Best Seller"
                }
            ],
            "status": "success"
        }

    if search_results.get("status") == "error":
        print(f"Error during search: {search_results.get('errorMessage')}")
        return None

    products = search_results.get("products", [])
    if not products:
        print("No products found matching the keyword.")
        return None

    # Pick the first non-sponsored product as a test prospect candidate
    target_prospect = None
    for prod in products:
        if not prod.get("isSponsored"):
            target_prospect = prod
            break
    if not target_prospect:
        target_prospect = products[0]

    asin = target_prospect.get("asin")
    title = target_prospect.get("title")
    price = target_prospect.get("price", {}).get("amount")
    currency = target_prospect.get("price", {}).get("currencyCode")
    rating_val = target_prospect.get("rating", {}).get("value")
    review_ct = target_prospect.get("rating", {}).get("count")

    print(f"Selected Target ASIN: {asin}")
    print(f"Title: {title[:75]}...")
    print(f"Price: {price} {currency}, Rating: {rating_val} ({review_ct} reviews)\n")

    # 2. Extract detailed Product Data (PDP) to identify the brand name
    print("[Step 2] Retrieving detailed Product Pages (PDP) for brand verification...")
    if token_set:
        pdp_results = amazon_scraper.get_pdp(asin, geocode)
    else:
        pdp_results = {
            "asin": asin,
            "brand": "Gogoonike",
            "name": title,
            "url": f"https://www.amazon.com/dp/{asin}",
            "rating": rating_val,
            "total_ratings": review_ct,
            "price": price,
            "currency": currency,
            "is_prime": True,
            "best_seller_rankings": [
                { "category": "Office Products", "rank": 249 },
                { "category": "Laptop Stands", "rank": 2 }
            ],
            "status": "success"
        }

    if pdp_results.get("status") == "error":
        print(f"Error during PDP retrieval: {pdp_results.get('errorMessage')}")
        return None

    brand = pdp_results.get("brand")
    bsr = pdp_results.get("best_seller_rankings", [])
    print(f"Extracted Brand: {brand}")
    print(f"Best Sellers Rankings: {bsr}\n")

    # 3. Retrieve Seller Offers list to examine Seller vs Brand matching
    print("[Step 3] Retrieving all Seller Offers...")
    if token_set:
        offers_results = amazon_scraper.get_offers(asin, geocode)
    else:
        offers_results = {
            "asin": asin,
            "offers": [
                {
                    "condition": "New",
                    "merchantName": "Gogoonike Direct",
                    "shipsFrom": "United States",
                    "isBuyBoxWinner": True,
                    "isFulfilledByAmazon": True,
                    "sellerId": "A1B2C3D4E5F6G7"
                },
                {
                    "condition": "New",
                    "merchantName": "Generic Reseller LLC",
                    "shipsFrom": "China",
                    "isBuyBoxWinner": False,
                    "isFulfilledByAmazon": False,
                    "sellerId": "A9Z8Y7X6W5V4"
                }
            ],
            "status": "success"
        }

    if offers_results.get("status") == "error":
        print(f"Error during Offers retrieval: {offers_results.get('errorMessage')}")
        return None

    offers = offers_results.get("offers", [])
    print(f"Found {len(offers)} active seller offer(s).")

    seller_matching_info = []
    brand_sells_own_product = False
    for off in offers:
        merchant_name = off.get("merchantName", "Unknown")
        ships_from = off.get("shipsFrom", "Unknown")
        is_fba = off.get("isFulfilledByAmazon", False)
        is_buybox = off.get("isBuyBoxWinner", False)
        seller_id = off.get("sellerId")

        # Compare brand name with merchant name (loose case-insensitive comparison)
        brand_match = False
        if brand and merchant_name:
            brand_match = (brand.lower() in merchant_name.lower()) or (merchant_name.lower() in brand.lower())
            if brand_match:
                brand_sells_own_product = True

        seller_matching_info.append({
            "merchantName": merchant_name,
            "shipsFrom": ships_from,
            "isFulfilledByAmazon": is_fba,
            "isBuyBoxWinner": is_buybox,
            "sellerId": seller_id,
            "matchesBrand": brand_match
        })
        print(f" - Seller: '{merchant_name}' (ID: {seller_id}) | Ships from: {ships_from} | FBA: {is_fba} | Buy Box: {is_buybox} | Matches Brand: {brand_match}")
    print()

    # 4. Pass verified brand name into the Agent-Reach research workflow
    print("[Step 4] Handing over verified Brand Candidate to Agent-Reach for web/company research...")

    # Simulating Jina Reader & Exa target pipeline
    combined_record = {
        "marketplace": geocode.upper(),
        "search_keyword": keyword,
        "asin": asin,
        "title": title,
        "brand": brand,
        "url": f"https://www.amazon.com/dp/{asin}",
        "price": price,
        "rating": rating_val,
        "reviewCount": review_ct,
        "bsr": bsr,
        "brand_sells_own_product_evidence": brand_sells_own_product,
        "offers": seller_matching_info,
        "agent_reach_handover": {
            "targets": {
                "dtc_website_query": f"\"{brand}\" official website",
                "hiring_growth_signals": f"\"{brand}\" hiring \"Amazon\" OR \"marketplace\"",
                "decision_maker_linkedin": f"\"{brand}\" founder OR CEO linkedin"
            },
            "routing": "Agent-Reach search category Web/Social/Career"
        }
    }

    print("\n--- COMBINED INTEGRATION JSON OUTPUT ---")
    print(json.dumps(combined_record, indent=2))
    return combined_record

if __name__ == "__main__":
    keyword = "laptop stands"
    run_integration_pipeline(keyword, "us")
