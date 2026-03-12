from app.models import User, InventoryStaff


class StaffRepository:
    def get_all(self):
        return InventoryStaff.objects.select_related("user").all()

    def get_by_id(self, pk):
        return InventoryStaff.objects.select_related("user").filter(pk=pk).first()

    def get_by_storage_code(self, code):
        return InventoryStaff.objects.filter(storage_code=code).first()

    def get_user_by_username(self, username: str):
        return User.objects.filter(username=username).first()

    def get_user_by_email(self, email: str):
        return User.objects.filter(email=email).first()

    def get_staff_by_user_id(self, user_id: int):
        return InventoryStaff.objects.select_related("user").filter(user_id=user_id).first()

    def create_user(self, **kwargs) -> User:
        return User.objects.create(**kwargs)

    def create_staff(self, user: User, **kwargs) -> InventoryStaff:
        return InventoryStaff.objects.create(user=user, **kwargs)

    def update(self, staff: InventoryStaff, **kwargs) -> InventoryStaff:
        for k, v in kwargs.items():
            setattr(staff, k, v)
        staff.save()
        return staff

    def delete(self, staff: InventoryStaff) -> None:
        staff.user.delete()
