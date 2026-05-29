from django.db import transaction
from .models import Cart, CartItem

class CartService:
    def get_cart(self, customer_id: int):
        cart, created = Cart.objects.get_or_create(customer_id=customer_id)
        return cart

    def add_item(self, customer_id: int, product_id: int, quantity: int, unit_price: float = 0):
        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0")
            
        with transaction.atomic():
            cart = self.get_cart(customer_id)
            item, created = CartItem.objects.get_or_create(
                cart=cart, product_id=product_id,
                defaults={"quantity": quantity, "unit_price": unit_price}
            )
            
            if not created:
                item.quantity += quantity
                item.unit_price = unit_price # Update snapshot price
                item.save(update_fields=["quantity", "unit_price"])
                
        return self.get_cart(customer_id)

    def update_item(self, customer_id: int, product_id: int, quantity: int):
        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0")
            
        with transaction.atomic():
            cart = self.get_cart(customer_id)
            item = CartItem.objects.filter(cart=cart, product_id=product_id).first()
            if item:
                item.quantity = quantity
                item.save(update_fields=["quantity"])
            else:
                raise ValueError("Item not found in cart")
                
        return self.get_cart(customer_id)

    def remove_item(self, customer_id: int, product_id: int):
        with transaction.atomic():
            cart = self.get_cart(customer_id)
            CartItem.objects.filter(cart=cart, product_id=product_id).delete()
        return self.get_cart(customer_id)

    def clear_cart(self, customer_id: int):
        with transaction.atomic():
            cart = self.get_cart(customer_id)
            CartItem.objects.filter(cart=cart).delete()
        return self.get_cart(customer_id)
