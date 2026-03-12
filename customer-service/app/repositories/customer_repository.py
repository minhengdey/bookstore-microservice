from app.models import Customer


class CustomerRepository:
    def get_all(self):
        return Customer.objects.select_related("user").all()

    def get_by_id(self, customer_id: int):
        return Customer.objects.select_related("user").filter(pk=customer_id).first()

    def get_by_user_id(self, user_id: int):
        return Customer.objects.select_related("user").filter(user_id=user_id).first()

    def create(self, user, **kwargs) -> Customer:
        return Customer.objects.create(user=user, **kwargs)

    def update(self, customer: Customer, **kwargs) -> Customer:
        for field, value in kwargs.items():
            setattr(customer, field, value)
        customer.save()
        return customer

    def delete(self, customer: Customer) -> None:
        customer.delete()

    def add_loyalty_points(self, customer: Customer, points: int) -> Customer:
        customer.loyalty_points += points
        customer.save(update_fields=["loyalty_points"])
        return customer
