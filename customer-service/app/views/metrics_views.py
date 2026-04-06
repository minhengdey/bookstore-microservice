from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from app.models import Customer
import hashlib

class CustomerMetricsView(APIView):
    """
    Endpoint nội bộ dành cho recommender-ai-service.
    Trả về dữ liệu gốc và dữ liệu giả lập (age, gender, location_id)
    do Database chưa có các trường này.
    """
    permission_classes = [permissions.AllowAny] # Trong microservice nội bộ qua docker network

    def get(self, request):
        customers = Customer.objects.all()
        data = []
        for c in customers:
            # Dùng hashlib để tạo giá trị giả lập cố định theo ID user (giữ tính nhất quán)
            hash_val = int(hashlib.md5(str(c.user.id).encode()).hexdigest(), 16)
            
            # Tuổi ngẫu nhiên từ 18 -> 65 (normalize 0->1 cho Pytorch)
            age = 18 + (hash_val % 47)
            age_norm = age / 100.0
            
            # Giới tính: 0 (Nữ) hoặc 1 (Nam)
            gender = float((hash_val >> 4) % 2)
            
            # Vị trí: 1 -> 50
            location_id = 1 + ((hash_val >> 8) % 50)
            
            data.append({
                "user_id": c.user.id,
                "age_normalized": age_norm,
                "gender": gender,
                "location_id": location_id
            })
            
        return Response(data)
