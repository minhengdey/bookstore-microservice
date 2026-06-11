from django.urls import path, include
from rest_framework.routers import DefaultRouter
from interaction.views.views import InteractionViewSet, ReviewViewSet, WishlistViewSet, TicketViewSet, TicketReplyViewSet

router = DefaultRouter()
router.register(r'interactions', InteractionViewSet, basename='interaction')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'wishlists', WishlistViewSet, basename='wishlist')
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'ticket-replies', TicketReplyViewSet, basename='ticket-reply')

urlpatterns = [
    path('', include(router.urls)),
]
