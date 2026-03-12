from app.models import WebAddress, Customer


class WebAddressRepository:
    def get_by_customer(self, customer: Customer):
        return WebAddress.objects.filter(customer=customer)

    def get_by_id(self, address_id: int):
        return WebAddress.objects.filter(pk=address_id).first()

    def get_default(self, customer: Customer):
        return WebAddress.objects.filter(customer=customer, is_default=True).first()

    def create(self, customer: Customer, **kwargs) -> WebAddress:
        return WebAddress.objects.create(customer=customer, **kwargs)

    def update(self, address: WebAddress, **kwargs) -> WebAddress:
        for field, value in kwargs.items():
            setattr(address, field, value)
        address.save()
        return address

    def delete(self, address: WebAddress) -> None:
        address.delete()

    def set_default(self, customer: Customer, address: WebAddress) -> None:
        WebAddress.objects.filter(customer=customer).update(is_default=False)
        address.is_default = True
        address.save(update_fields=["is_default"])
