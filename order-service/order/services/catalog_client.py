import os
import requests
import logging

logger = logging.getLogger(__name__)

class CatalogClient:
    @staticmethod
    def get_variant(variant_id: str):
        catalog_url = os.environ.get('CATALOG_SERVICE_URL', 'http://catalog-service:8000')
        url = f"{catalog_url}/api/v1/catalog/variants/{variant_id}/"
        try:
            # We don't necessarily need HMAC for a simple public read, but can include if needed
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                logger.error(f"Catalog API error: {response.status_code} - {response.text}")
                raise Exception("Catalog service unavailable")
        except requests.RequestException as e:
            logger.error(f"Catalog API connection error: {e}")
            raise Exception("Catalog service unavailable")
