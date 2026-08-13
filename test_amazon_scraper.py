import os
import unittest
from unittest.mock import patch, MagicMock

# Import module manually as Python sys modules cannot load hyphens
import importlib.util
spec = importlib.util.spec_from_file_location(
    "amazon_scraper", "/app/agent/skills/agent-reach/tools/amazon/amazon_scraper.py"
)
amazon_scraper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(amazon_scraper_module)

class TestAmazonScraper(unittest.TestCase):

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_token_graceful_exit(self):
        with self.assertRaises(SystemExit) as cm:
            amazon_scraper_module.get_token()
        self.assertEqual(cm.exception.code, 1)

    @patch.dict(os.environ, {"SCRAPEDO_API_TOKEN": "mock-test-token"})
    @patch("requests.get")
    def test_search_amazon_api_mapping(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success", "products": []}
        mock_get.return_value = mock_response

        res = amazon_scraper_module.search_amazon("wireless mouse", "us", 1)

        self.assertEqual(res["status"], "success")
        mock_get.assert_called_once_with(
            "https://api.scrape.do/plugin/amazon/search?token=mock-test-token&keyword=wireless%20mouse&geocode=us&page=1",
            timeout=30
        )

    @patch.dict(os.environ, {"SCRAPEDO_API_TOKEN": "mock-test-token"})
    @patch("requests.get")
    def test_get_pdp_api_mapping(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success", "brand": "Logitech"}
        mock_get.return_value = mock_response

        res = amazon_scraper_module.get_pdp("B0C7BKZ883", "gb")

        self.assertEqual(res["brand"], "Logitech")
        mock_get.assert_called_once_with(
            "https://api.scrape.do/plugin/amazon/pdp?token=mock-test-token&asin=B0C7BKZ883&geocode=gb",
            timeout=30
        )

    @patch.dict(os.environ, {"SCRAPEDO_API_TOKEN": "mock-test-token"})
    @patch("requests.get")
    def test_get_offers_api_mapping(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success", "offers": []}
        mock_get.return_value = mock_response

        res = amazon_scraper_module.get_offers("B0DGJ7HYG1", "us")

        self.assertEqual(res["status"], "success")
        mock_get.assert_called_once_with(
            "https://api.scrape.do/plugin/amazon/offer-listing?token=mock-test-token&asin=B0DGJ7HYG1&geocode=us",
            timeout=30
        )

if __name__ == "__main__":
    unittest.main()
