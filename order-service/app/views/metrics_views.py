from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from app.models import Order

class OrderMetricsView(APIView):
    """
    Endpoint nội bộ dành cho recommender-ai-service.
    Trả về danh sách khách hàng và mảng các book_id họ đã mua.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Optimize query by prefetching items
        orders = Order.objects.prefetch_related('items').all()
        
        # Group by customer_id
        customer_history = {}
        for order in orders:
            cid = order.customer_id
            if cid not in customer_history:
                customer_history[cid] = []
                
            for item in order.items.all():
                customer_history[cid].append(item.book_id)
                
        # Format for AI model
        data = []
        for cid, book_ids in customer_history.items():
            data.append({
                "customer_id": cid,
                "purchase_ids": book_ids
            })
            
        return Response(data)
