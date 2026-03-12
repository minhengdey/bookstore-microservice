from app.models import Cart, CartItem


class CartRepository:
    def get_by_customer(self, customer_id: int):
        return Cart.objects.filter(customer_id=customer_id).prefetch_related("items").first()

    def get_cart_by_id(self, cart_id: int):
        return Cart.objects.filter(pk=cart_id).prefetch_related("items").first()

    def create_cart(self, customer_id: int) -> Cart:
        return Cart.objects.create(customer_id=customer_id)

    def get_or_create_cart(self, customer_id: int):
        return Cart.objects.get_or_create(customer_id=customer_id)

    def delete_cart(self, cart: Cart) -> None:
        cart.delete()

    # ── CartItem ──────────────────────────────────────────────────────────────

    def get_item(self, cart: Cart, book_id: int):
        return CartItem.objects.filter(cart=cart, book_id=book_id).first()

    def get_item_by_id(self, item_id: int):
        return CartItem.objects.filter(pk=item_id).first()

    def add_item(self, cart: Cart, book_id: int, quantity: int, unit_price: float) -> CartItem:
        item = self.get_item(cart, book_id)
        if item:
            item.quantity += quantity
            item.save(update_fields=["quantity"])
            return item
        return CartItem.objects.create(cart=cart, book_id=book_id, quantity=quantity, unit_price=unit_price)

    def update_item_quantity(self, item: CartItem, quantity: int) -> CartItem:
        item.quantity = quantity
        item.save(update_fields=["quantity"])
        return item

    def remove_item(self, item: CartItem) -> None:
        item.delete()

    def clear_cart(self, cart: Cart) -> None:
        CartItem.objects.filter(cart=cart).delete()
