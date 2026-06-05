import requests

def test_order():
    payload = {
        "customer_id": 1,
        "items": [
            {"product_id": 1, "quantity": 1, "unit_price": 1000}
        ],
        "shipping_fee": 0,
        "notes": "Test"
    }
    
    headers = {
        "X-User-Id": "1",
        "X-Role": "customer",
        "X-Entity-Id": "1"
    }
    
    try:
        r2 = requests.post("http://localhost:8007/orders/", json=payload, headers=headers, timeout=5)
        print("LEGACY STATUS:", r2.status_code)
        print("LEGACY TEXT:", r2.text)
    except Exception as e:
        print("LEGACY ERROR:", e)

if __name__ == "__main__":
    test_order()
