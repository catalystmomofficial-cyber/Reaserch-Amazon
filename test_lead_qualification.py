import unittest
import sys
import importlib.util

# Dynamically import the canonical qualification engine
spec = importlib.util.spec_from_file_location(
    "lead_qualification_engine", ".agents/skills/agent-reach/tools/amazon/lead_qualification_engine.py"
)
lqe_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lqe_module)

class TestLeadQualificationEngine(unittest.TestCase):

    def setUp(self):
        # Baseline ideal mock data payload
        self.ideal_amazon_data = {
            "brand_name": "Nulaxy",
            "country": "US",
            "category": "electronics accessories",
            "marketplace": "US",
            "storefront_url": "https://www.amazon.com/stores/Nulaxy",
            "primary_asin": "B077B9W343",
            "product_title": "Nulaxy Ergonomic Adjustable Laptop Stand for Desk",
            "price_amount": 15.99,
            "price_currency": "USD",
            "ratings_average": 4.8,
            "total_ratings_count": 14200,
            "best_seller_rank_min": 1,
            "search_page_position": 1,
            "brand_ownership_verified": "Yes",
            "buy_box_owner": "Woot",
            "ships_from": "Unknown",
            "brand_owns_buybox": False,
            "is_fba": False,
            "buy_box_stolen_by_resellers": True,
            "has_negative_review_trends": False,
            "sku_catalog_count": 12,
            "listing_gaps": {
                "missing_video": True,
                "missing_aplus_content": True,
                "poor_image_hierarchy": True
            },
            "storefront_design_optimized": False,
            "amazon_listings_underoptimized": True
        }

        self.ideal_web_data = {
            "website_url": "https://www.nulaxy.com",
            "revenue_usd": 5000000,
            "employee_count": 25,
            "decision_maker_name": "James Zhang",
            "decision_maker_profile": {
                "title": "Director of E-Commerce",
                "linkedin_url": "https://linkedin.com/in/james-zhang-nulaxy",
                "linkedin_verified": True,
                "email": "james@nulaxy.com"
            },
            "dtc_strength": {
                "is_stunning_shopify": True,
                "is_active_dtc": True
            },
            "maturity": {
                "has_funding": True
            },
            "intent": {
                "is_hiring_ecommerce_roles": True,
                "active_expansion_news": True
            }
        }

    # 1. Test Case: Ideal Grade A+ Brand (Nulaxy / Woot Validation Fixture)
    def test_nulaxy_woot_validation_fixture(self):
        engine = lqe_module.LeadQualificationEngine(self.ideal_amazon_data, self.ideal_web_data)
        res = engine.evaluate()

        self.assertFalse(engine.is_rejected)
        self.assertEqual(engine.grade, "A+")
        self.assertEqual(engine.status, "QUALIFIED FOR OUTREACH")
        self.assertEqual(res["qualification_analysis"]["publicly_observed_amazon_opportunities"][0]["fact"],
                         "No product explainer video is present in the main listing media slots.")
        self.assertTrue(res["amazon_verification_evidence"]["brand_ownership_facts"]["is_buy_box_winner"] is False)
        # Verify strict 3-request Scrape.do API budget count
        self.assertEqual(res["scoring_and_outreach"]["api_budget_enforcement"]["scraped_urls_count"], 3)

    # 2. Test Case: Grade B Potential Brand (Moderate score)
    def test_grade_b_potential_brand(self):
        # Alter baseline so that points drop slightly but avoids hard rejection
        amazon = self.ideal_amazon_data.copy()
        amazon["best_seller_rank_min"] = 30000  # Only 5 points here
        amazon["buy_box_stolen_by_resellers"] = False # Stolen buy box points dropped
        amazon["listing_gaps"] = {
            "missing_video": True,
            "missing_aplus_content": False,
            "poor_image_hierarchy": False
        }

        web = self.ideal_web_data.copy()
        web["dtc_strength"] = {"is_stunning_shopify": False, "is_active_dtc": True}
        web["intent"] = {"is_hiring_ecommerce_roles": False, "active_expansion_news": False}

        engine = lqe_module.LeadQualificationEngine(amazon, web)
        res = engine.evaluate()

        self.assertFalse(engine.is_rejected)
        self.assertEqual(engine.grade, "B")
        self.assertEqual(engine.status, "PROMISING — NEEDS HUMAN VERIFICATION")

    # 3. Test Case: Grade C / Rejected Reseller (Hard Rejection Rule 2)
    def test_grade_c_rejected_reseller(self):
        amazon = self.ideal_amazon_data.copy()
        amazon["brand_ownership_verified"] = "No" # Unverified owner / reseller trigger

        engine = lqe_module.LeadQualificationEngine(amazon, self.ideal_web_data)
        res = engine.evaluate()

        self.assertTrue(engine.is_rejected)
        self.assertEqual(engine.grade, "C")
        self.assertEqual(engine.status, "REJECTED")
        self.assertIn("Unverified Brand Ownership", "".join(res["scoring_and_outreach"]["api_budget_enforcement"]["rejections_triggered"]))

    # 4. Test Case: Non-US/UK Company (Hard Rejection Rule 1)
    def test_non_us_uk_company(self):
        amazon = self.ideal_amazon_data.copy()
        amazon["country"] = "DE" # Non US/UK geocode

        engine = lqe_module.LeadQualificationEngine(amazon, self.ideal_web_data)
        res = engine.evaluate()

        self.assertTrue(engine.is_rejected)
        self.assertEqual(engine.grade, "C")
        self.assertIn("Geographic Mismatch", "".join(res["scoring_and_outreach"]["api_budget_enforcement"]["rejections_triggered"]))

    # 5. Test Case: Brand with Unverified Ownership (Same as Reseller Check)
    def test_brand_with_unverified_ownership(self):
        amazon = self.ideal_amazon_data.copy()
        amazon["brand_ownership_verified"] = "No"

        engine = lqe_module.LeadQualificationEngine(amazon, self.ideal_web_data)
        res = engine.evaluate()

        self.assertTrue(engine.is_rejected)
        self.assertEqual(res["amazon_verification_evidence"]["brand_ownership_verified"], "No")

    # 6. Test Case: Brand with Strong Amazon Presence but No Identifiable Gaps (Hard Rejection Rule 6)
    def test_strong_amazon_no_problem(self):
        amazon = self.ideal_amazon_data.copy()
        amazon["listing_gaps"] = {
            "missing_video": False,
            "missing_aplus_content": False,
            "poor_image_hierarchy": False
        }
        amazon["storefront_design_optimized"] = True
        amazon["buy_box_stolen_by_resellers"] = False

        engine = lqe_module.LeadQualificationEngine(amazon, self.ideal_web_data)
        res = engine.evaluate()

        self.assertTrue(engine.is_rejected)
        self.assertEqual(engine.grade, "C")
        self.assertIn("Fully Optimized Store", "".join(res["scoring_and_outreach"]["api_budget_enforcement"]["rejections_triggered"]))

    # 7. Test Case: Brand with Strong DTC Presence but Weak Amazon Execution
    def test_strong_dtc_weak_amazon(self):
        amazon = self.ideal_amazon_data.copy()
        amazon["listing_gaps"] = {
            "missing_video": True,
            "missing_aplus_content": True,
            "poor_image_hierarchy": True
        }
        amazon["amazon_listings_underoptimized"] = True

        web = self.ideal_web_data.copy()
        web["dtc_strength"] = {
            "is_stunning_shopify": True,
            "is_active_dtc": True
        }

        engine = lqe_module.LeadQualificationEngine(amazon, web)
        res = engine.evaluate()

        self.assertFalse(engine.is_rejected)
        # Ensure DTC execution gap points are correctly scored
        self.assertEqual(engine.scores_breakdown["dtc_gap"], 10)
        self.assertTrue(engine.total_score >= 80)

    # 8. Test Case: Third-party Seller / Buy Box hijacked Problem
    def test_third_party_buy_box_hijacked(self):
        amazon = self.ideal_amazon_data.copy()
        amazon["buy_box_stolen_by_resellers"] = True

        engine = lqe_module.LeadQualificationEngine(amazon, self.ideal_web_data)
        res = engine.evaluate()

        self.assertFalse(engine.is_rejected)
        # Stolen buy box awards 10 points
        self.assertEqual(engine.scores_breakdown["pain_evidence"], 10)

    # 9. Test Case: Fact vs Evidence vs Inference Separation
    def test_evidence_vs_inference_separation(self):
        engine = lqe_module.LeadQualificationEngine(self.ideal_amazon_data, self.ideal_web_data)
        res = engine.evaluate()

        opp = res["qualification_analysis"]["publicly_observed_amazon_opportunities"][0]
        self.assertIn("fact", opp)
        self.assertIn("evidence_url", opp)
        self.assertIn("inference", opp)

    # 10. Test Case: 3-Request Scrape.do Limit enforcement
    def test_three_request_limit_budget_enforcement(self):
        engine = lqe_module.LeadQualificationEngine(self.ideal_amazon_data, self.ideal_web_data)
        res = engine.evaluate()

        # Ensure budget enforcer is populated
        self.assertEqual(res["scoring_and_outreach"]["api_budget_enforcement"]["scraped_urls_count"], 3)

        # Rejected leads shouldn't fire offers check, so count should be capped at 2
        amazon = self.ideal_amazon_data.copy()
        amazon["country"] = "DE"
        engine_rejected = lqe_module.LeadQualificationEngine(amazon, self.ideal_web_data)
        res_rejected = engine_rejected.evaluate()
        self.assertEqual(res_rejected["scoring_and_outreach"]["api_budget_enforcement"]["scraped_urls_count"], 2)

    # 11. Test Case: 28-field Schema validation
    def test_schema_field_presence_validation(self):
        engine = lqe_module.LeadQualificationEngine(self.ideal_amazon_data, self.ideal_web_data)
        res = engine.evaluate()

        # Group 1: brand_identity
        self.assertIn("brand_name", res["brand_identity"])
        self.assertIn("country", res["brand_identity"])
        self.assertIn("category", res["brand_identity"])
        self.assertIn("website_url", res["brand_identity"])

        # Group 2: amazon_market_presence
        self.assertIn("marketplace", res["amazon_market_presence"])
        self.assertIn("storefront_url", res["amazon_market_presence"])
        self.assertIn("primary_asin", res["amazon_market_presence"])
        self.assertIn("product_title", res["amazon_market_presence"])
        self.assertIn("product_url", res["amazon_market_presence"])
        self.assertIn("list_price", res["amazon_market_presence"])
        self.assertIn("currency_code", res["amazon_market_presence"])
        self.assertIn("ratings_average", res["amazon_market_presence"])
        self.assertIn("total_ratings_count", res["amazon_market_presence"])
        self.assertIn("best_seller_rank", res["amazon_market_presence"])
        self.assertIn("search_page_position", res["amazon_market_presence"])

        # Group 3: amazon_verification_evidence
        self.assertIn("brand_ownership_verified", res["amazon_verification_evidence"])
        self.assertIn("brand_ownership_facts", res["amazon_verification_evidence"])
        self.assertIn("seller_offers_evidence_url", res["amazon_verification_evidence"])

        # Group 4: qualification_analysis
        self.assertIn("publicly_observed_amazon_opportunities", res["qualification_analysis"])
        self.assertIn("confirmed_customer_pain", res["qualification_analysis"])
        self.assertIn("dtc_brand_strength_signals", res["qualification_analysis"])
        self.assertIn("growth_and_hiring_intent_signals", res["qualification_analysis"])

        # Group 5: decision_maker_profile
        self.assertIn("contact_name", res["decision_maker_profile"])
        self.assertIn("job_title", res["decision_maker_profile"])
        self.assertIn("linkedin_url", res["decision_maker_profile"])
        self.assertIn("business_email", res["decision_maker_profile"])

        # Group 6: scoring_and_outreach
        self.assertIn("qualification_score", res["scoring_and_outreach"])
        self.assertIn("qualification_grade", res["scoring_and_outreach"])
        self.assertIn("qualification_status", res["scoring_and_outreach"])
        self.assertIn("reason_for_qualification", res["scoring_and_outreach"])
        self.assertIn("recommended_outreach_angle", res["scoring_and_outreach"])

    # 12. Test Case: Multiple Candidate Ranking and sorting
    def test_candidate_ranking(self):
        # Mocking multiple brands
        amazon_b = self.ideal_amazon_data.copy()
        amazon_b["best_seller_rank_min"] = 30000
        amazon_b["buy_box_stolen_by_resellers"] = False
        amazon_b["listing_gaps"] = {
            "missing_video": True,
            "missing_aplus_content": False,
            "poor_image_hierarchy": False
        }

        web_b = self.ideal_web_data.copy()
        web_b["dtc_strength"] = {"is_stunning_shopify": False, "is_active_dtc": True}
        web_b["intent"] = {"is_hiring_ecommerce_roles": False, "active_expansion_news": False}

        amazon_c = self.ideal_amazon_data.copy()
        amazon_c["brand_ownership_verified"] = "No"

        # Initialize engines
        engine_a = lqe_module.LeadQualificationEngine(self.ideal_amazon_data, self.ideal_web_data)
        engine_b = lqe_module.LeadQualificationEngine(amazon_b, web_b)
        engine_c = lqe_module.LeadQualificationEngine(amazon_c, self.ideal_web_data)

        # Run evaluations
        lead_a = engine_a.evaluate()
        lead_b = engine_b.evaluate()
        lead_c = engine_c.evaluate()

        leads_list = [lead_b, lead_c, lead_a]

        # Sort leads list: Higher score first, putting rejected/lowest score last
        sorted_leads = sorted(leads_list, key=lambda x: x["scoring_and_outreach"]["qualification_score"], reverse=True)

        self.assertEqual(sorted_leads[0]["brand_identity"]["brand_name"], "Nulaxy") # Grade A+ (Score 95)
        self.assertEqual(sorted_leads[1]["scoring_and_outreach"]["qualification_grade"], "B") # Grade B
        self.assertEqual(sorted_leads[2]["scoring_and_outreach"]["qualification_grade"], "C") # Grade C / Reject

if __name__ == "__main__":
    unittest.main()
