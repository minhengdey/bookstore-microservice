import os
import requests
import warnings
import random

def fetch_real_training_data():
    """
    Kéo dữ liệu thật từ Customer Service và Order Service.
    Nếu không gọi được, trả về None để hệ thống dùng dữ liệu giả.
    """
    customer_url = os.environ.get("CUSTOMER_SERVICE_URL", "http://customer-service:8000")
    order_url = os.environ.get("ORDER_SERVICE_URL", "http://order-service:8000")
    
    try:
        # Lưu ý: Các route này kết nối qua Docker Network nội bộ
        cust_resp = requests.get(f"{customer_url}/api/customers/metrics/", timeout=3)
        order_resp = requests.get(f"{order_url}/api/orders/metrics/", timeout=3)
        
        if cust_resp.status_code == 200 and order_resp.status_code == 200:
            customers = cust_resp.json()
            orders = order_resp.json()
            
            # Khớp orders theo user_id để tra cứu nhanh (O(1))
            order_dict = {o["customer_id"]: o["purchase_ids"] for o in orders}
            
            merged_data = []
            for c in customers:
                uid = c["user_id"]
                p_ids = order_dict.get(uid, [])
                
                # Interacted services: Random giả lập dựa theo purchase behavior
                # VD: User ID chẵn ưu tiên service 2, 4. Lẻ ưu tiên 1, 3.
                interacted = []
                if p_ids:
                    # Gán đại 1-2 ID của dịch vụ dựa trên mã sách họ mua đầu tiên
                    first_book = p_ids[0]
                    interacted.append(first_book % 15) # Assuming 15 services (0..14 index)
                else:
                    interacted.append(uid % 15)
                    
                merged_data.append({
                    "user_id": uid,
                    "age_normalized": c["age_normalized"],
                    "gender": c["gender"],
                    "location_id": c["location_id"],
                    "purchase_ids": p_ids,
                    "browsing_ids": p_ids, # Giả lập browsing y hệt purchase do thiếu tracking
                    "interacted_service_indices": interacted
                })
                
            return merged_data if merged_data else None
            
        else:
            return None
    except requests.exceptions.RequestException as e:
        warnings.warn(f"[DataSync] Failed to fetch data. Error: {e}")
        return None
