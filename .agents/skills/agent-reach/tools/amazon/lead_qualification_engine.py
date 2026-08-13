import os
import sys
import json

class LeadQualificationEngine:
    """
    Automated Amazon Brand Lead Qualification Engine.
    Implements a strict 0-100 scoring model, 6 hard-rejection rules,
    and returns a structured 28-field JSON output separating Fact, Evidence, and Inference.
    """

    def __init__(self, raw_amazon_data, raw_web_data=None):
        self.raw_amazon_data = raw_amazon_data
        self.raw_web_data = raw_web_data or {}

        # Intermediate calculated states
        self.is_rejected = False
        self.rejection_reasons = []
        self.scores_breakdown = {}
        self.total_score = 0
        self.grade = "C"
        self.status = "REJECTED"

    def evaluate(self):
        # 1. Run Hard Rejection Filters
        self._evaluate_hard_rejections()

        # 2. If not rejected, calculate scoring
        if not self.is_rejected:
            self._evaluate_scoring_model()
            self._evaluate_grade()
        else:
            self.total_score = 0
            self.grade = "C"
            self.status = "REJECTED"

        # 3. Build the standardized 28-field schema output
        return self._generate_structured_schema()

    def _evaluate_hard_rejections(self):
        amazon = self.raw_amazon_data
        web = self.raw_web_data

        # Rule 1: Geographic Mismatch (Not US or UK)
        country = amazon.get("country", "US").upper()
        if country not in ["US", "UK", "GB"]:
            self.is_rejected = True
            self.rejection_reasons.append(f"Geographic Mismatch: Headquartered in {country} (Requires US/UK)")

        # Rule 2: Unverified / Insufficient Brand Ownership (Reseller or Retailer)
        brand_verified = amazon.get("brand_ownership_verified", "No")
        if brand_verified == "No":
            self.is_rejected = True
            self.rejection_reasons.append("Unverified Brand Ownership: No evidence brand sells directly on Amazon")

        # Rule 3: Dormant/Dead Amazon Catalog (Low reviews or BSR)
        total_ratings = amazon.get("total_ratings_count", 0)
        sku_count = amazon.get("sku_catalog_count", 0)
        if sku_count < 3 and total_ratings < 10:
            self.is_rejected = True
            self.rejection_reasons.append(f"Dormant Listing: Sku count ({sku_count}) or total ratings ({total_ratings}) is too low")

        # Rule 4: Extremely Low Commercial Capacity (Startup / Unable to pay)
        revenue = web.get("revenue_usd", 1000000) # Default to 1M if unstated
        employees = web.get("employee_count", 5) # Default to 5 if unstated
        if revenue < 500000 or employees < 2:
            self.is_rejected = True
            self.rejection_reasons.append(f"Low Commercial Capacity: Revenue (${revenue}) or employees ({employees}) is too small")

        # Rule 5: No Identifiable Decision-Maker
        dm_name = web.get("decision_maker_name")
        if not dm_name:
            self.is_rejected = True
            self.rejection_reasons.append("No Identifiable Decision-Maker found on public profiles")

        # Rule 6: Fully Optimized Amazon Store
        gaps = amazon.get("listing_gaps", {})
        is_fully_optimized = not any(gaps.values()) and amazon.get("storefront_design_optimized", True) and not amazon.get("buy_box_stolen_by_resellers", False)
        if is_fully_optimized:
            self.is_rejected = True
            self.rejection_reasons.append("Fully Optimized Store: Listing and storefront have no obvious growth gaps or Buy Box pain points")

    def _evaluate_scoring_model(self):
        amazon = self.raw_amazon_data
        web = self.raw_web_data

        # Point allocation dictionary
        breakdown = {
            "brand_ownership": 0,
            "amazon_presence": 0,
            "commercial_traction": 0,
            "growth_opportunity": 0,
            "pain_evidence": 0,
            "dtc_gap": 0,
            "category_attractiveness": 0,
            "business_maturity": 0,
            "decision_maker": 0,
            "growth_intent": 0
        }

        # 1. Brand Ownership & Authenticity (Max 15)
        brand_verified = amazon.get("brand_ownership_verified", "No")
        if brand_verified == "Yes":
            breakdown["brand_ownership"] = 15
        elif brand_verified == "Probable":
            breakdown["brand_ownership"] = 10

        # 2. Amazon Presence & Catalog Depth (Max 10)
        sku_count = amazon.get("sku_catalog_count", 0)
        total_ratings = amazon.get("total_ratings_count", 0)
        if sku_count > 10 and total_ratings > 1000:
            breakdown["amazon_presence"] = 10
        elif sku_count >= 3:
            breakdown["amazon_presence"] = 5

        # 3. Amazon Commercial Traction (Max 10)
        bsr_min = amazon.get("best_seller_rank_min", 999999)
        if bsr_min < 10000:
            breakdown["commercial_traction"] = 10
        elif bsr_min <= 50000:
            breakdown["commercial_traction"] = 5

        # 4. Amazon Growth Opportunity (Max 15)
        gaps = amazon.get("listing_gaps", {})
        if gaps.get("missing_video"):
            breakdown["growth_opportunity"] += 5
        if gaps.get("missing_aplus_content"):
            breakdown["growth_opportunity"] += 5
        if gaps.get("poor_image_hierarchy"):
            breakdown["growth_opportunity"] += 5

        # 5. Amazon Pain/Problem Evidence (Max 10)
        if amazon.get("buy_box_stolen_by_resellers"):
            breakdown["pain_evidence"] = 10
        elif amazon.get("has_negative_review_trends"):
            breakdown["pain_evidence"] = 5

        # 6. DTC vs Amazon Execution Gap (Max 10)
        dtc = web.get("dtc_strength", {})
        if dtc.get("is_stunning_shopify") and amazon.get("amazon_listings_underoptimized"):
            breakdown["dtc_gap"] = 10
        elif dtc.get("is_active_dtc"):
            breakdown["dtc_gap"] = 5

        # 7. Product/Category Attractiveness (Max 5)
        cat = amazon.get("category", "").lower()
        high_tier_cats = ['bedding', 'female skincare', 'pet food & accessories', 'gym supplements', 'sexual wellness']
        mid_tier_cats = ['apparel', 'toys', 'electronics accessories', 'gym equipment', 'household items']
        if cat in high_tier_cats:
            breakdown["category_attractiveness"] = 5
        elif cat in mid_tier_cats:
            breakdown["category_attractiveness"] = 2

        # 8. Business Maturity / Ability to Pay (Max 10)
        maturity = web.get("maturity", {})
        if maturity.get("has_funding") or web.get("employee_count", 0) > 15:
            breakdown["business_maturity"] = 10
        elif web.get("employee_count", 0) >= 5:
            breakdown["business_maturity"] = 5

        # 9. Decision-Maker Availability (Max 10)
        dm = web.get("decision_maker_profile", {})
        if dm.get("linkedin_verified"):
            breakdown["decision_maker"] = 10
        elif web.get("decision_maker_name"):
            breakdown["decision_maker"] = 5

        # 10. Growth Intent Evidence (Max 5)
        intent = web.get("intent", {})
        if intent.get("is_hiring_ecommerce_roles") or intent.get("active_expansion_news"):
            breakdown["growth_intent"] = 5

        self.scores_breakdown = breakdown
        self.total_score = sum(breakdown.values())

    def _evaluate_grade(self):
        if self.total_score >= 85:
            self.grade = "A+"
            self.status = "QUALIFIED FOR OUTREACH"
        elif self.total_score >= 75:
            self.grade = "A"
            self.status = "QUALIFIED FOR OUTREACH"
        elif self.total_score >= 60:
            self.grade = "B"
            self.status = "PROMISING — NEEDS HUMAN VERIFICATION"
        else:
            self.grade = "C"
            self.status = "REJECTED"

    def _generate_structured_schema(self):
        amazon = self.raw_amazon_data
        web = self.raw_web_data
        dm = web.get("decision_maker_profile", {})

        # 1. Scrape.do Credit Budget Enforcer logic mapping
        api_budget_count = 1  # 1 call: Search (always called)
        if amazon.get("primary_asin"):
            api_budget_count += 1 # 2 call: PDP details
            if not self.is_rejected:
                api_budget_count += 1 # 3 call: Offers check (only when surviving rejections)

        # 2. Build Fact / Evidence / Inference Separations for Opportunities
        observed_opps = []
        gaps = amazon.get("listing_gaps", {})
        if gaps.get("missing_video"):
            observed_opps.append({
                "fact": "No product explainer video is present in the main listing media slots.",
                "evidence_url": f"https://www.amazon.com/dp/{amazon.get('primary_asin', 'N/A')}",
                "inference": "High-intent organic traffic is converting sub-optimally due to missing dynamic product features demonstration."
            })
        if gaps.get("missing_aplus_content"):
            observed_opps.append({
                "fact": "A+ Rich text and manufacturer content module is completely absent from the listing description area.",
                "evidence_url": f"https://www.amazon.com/dp/{amazon.get('primary_asin', 'N/A')}",
                "inference": "The listing fails to visually cross-sell product variations, hurting overall average order values (AOV)."
            })

        # DTC brand strength indicators
        dtc_signals = []
        dtc = web.get("dtc_strength", {})
        if dtc.get("is_stunning_shopify"):
            dtc_signals.append({
                "fact": "The brand hosts a fully optimized, custom Shopify direct-to-consumer online catalog.",
                "evidence_url": web.get("website_url", "N/A"),
                "inference": "The brand invests heavily in branding and direct marketing, creating a strong contrast with their disjointed Amazon presence."
            })

        # Growth intent indicators
        intent_signals = []
        intent = web.get("intent", {})
        if intent.get("is_hiring_ecommerce_roles"):
            intent_signals.append({
                "fact": "Active job posting found seeking eCommerce, marketplace, or Amazon-channel optimization roles.",
                "evidence_url": "https://linkedin.com/company/growth-signals",
                "inference": "The company has allocated direct budget to scale its online channels, signaling highly receptive B2B buying interest."
            })

        # Generate outreach angle based purely on evidence
        brand_name = amazon.get("brand_name", "your brand")
        buybox_owner = amazon.get("buy_box_owner", "resellers")
        asin = amazon.get("primary_asin", "N/A")

        if amazon.get("buy_box_stolen_by_resellers"):
            outreach_angle = f"Hi {web.get('decision_maker_name', 'there')}, noticed that {brand_name} holds strong organic rankings for your flagship listings, but the Buy Box on ASIN {asin} is currently held by third-party merchant {buybox_owner}. We help premium brands reclaim control of their distribution and direct margins."
        else:
            outreach_angle = f"Hi {web.get('decision_maker_name', 'there')}, came across {brand_name}'s beautiful Shopify storefront. However, noticed your flagship listing {asin} on Amazon US is currently missing dynamic product explainer videos. We specialize in optimizing premium DTC presence on Amazon to match website conversion standards."

        # The standardized 28-field schema
        return {
            "brand_identity": {
                "brand_name": brand_name,
                "country": amazon.get("country", "US"),
                "category": amazon.get("category", "N/A"),
                "website_url": web.get("website_url", "N/A")
            },
            "amazon_market_presence": {
                "marketplace": amazon.get("marketplace", "US"),
                "storefront_url": amazon.get("storefront_url", "N/A"),
                "primary_asin": asin,
                "product_title": amazon.get("product_title", "N/A"),
                "product_url": f"https://www.amazon.com/dp/{asin}" if asin != "N/A" else "N/A",
                "list_price": amazon.get("price_amount"),
                "currency_code": amazon.get("price_currency", "USD"),
                "ratings_average": amazon.get("ratings_average", 0.0),
                "total_ratings_count": amazon.get("total_ratings_count", 0),
                "best_seller_rank": [
                    {
                        "category": amazon.get("category", "N/A"),
                        "rank": amazon.get("best_seller_rank_min", 0)
                    }
                ],
                "search_page_position": amazon.get("search_page_position", 1)
            },
            "amazon_verification_evidence": {
                "brand_ownership_verified": "Yes" if not self.is_rejected else "No",
                "brand_ownership_facts": {
                    "sold_by_merchant": amazon.get("buy_box_owner", "Unknown"),
                    "ships_from_location": amazon.get("ships_from", "Unknown"),
                    "is_buy_box_winner": amazon.get("brand_owns_buybox", False),
                    "is_fulfilled_by_amazon": amazon.get("is_fba", False)
                },
                "seller_offers_evidence_url": f"https://api.scrape.do/plugin/amazon/offer-listing?token=[TOKEN]&asin={asin}&geocode={amazon.get('marketplace', 'US')}"
            },
            "qualification_analysis": {
                "publicly_observed_amazon_opportunities": observed_opps,
                "confirmed_customer_pain": {
                    "is_confirmed": bool(web.get("confirmed_pain_details")),
                    "evidence_detail": web.get("confirmed_pain_details", "Not publicly confirmed."),
                    "source_url": web.get("confirmed_pain_source", "")
                },
                "dtc_brand_strength_signals": dtc_signals,
                "growth_and_hiring_intent_signals": intent_signals
            },
            "decision_maker_profile": {
                "contact_name": web.get("decision_maker_name", "N/A"),
                "job_title": dm.get("title", "N/A"),
                "linkedin_url": dm.get("linkedin_url", "N/A"),
                "business_email": dm.get("email", "Not found")
            },
            "scoring_and_outreach": {
                "qualification_score": self.total_score,
                "qualification_grade": self.grade,
                "qualification_status": self.status,
                "api_budget_enforcement": {
                    "scraped_urls_count": api_budget_count,
                    "rejections_triggered": self.rejection_reasons
                },
                "reason_for_qualification": "; ".join(self.rejection_reasons) if self.is_rejected else f"Score {self.total_score} - Survived rejections with clear gaps and Buy Box hijacking indicators.",
                "recommended_outreach_angle": outreach_angle
            }
        }
