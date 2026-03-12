from django.contrib.auth.hashers import make_password
from app.repositories import StaffRepository


class StaffService:
    def __init__(self):
        self.repo = StaffRepository()

    def list_staff(self):
        return self.repo.get_all()

    def get_staff(self, pk):
        staff = self.repo.get_by_id(pk)
        if not staff:
            raise ValueError(f"Staff {pk} not found")
        return staff

    def create_staff(self, user_data: dict, staff_data: dict):
        if self.repo.get_user_by_username(user_data.get("username", "")):
            raise ValueError("Username already taken")
        if self.repo.get_user_by_email(user_data.get("email", "")):
            raise ValueError("Email already registered")
        raw_pw = user_data.pop("password", "")
        user_data["password"] = make_password(raw_pw)
        user  = self.repo.create_user(**user_data)
        return self.repo.create_staff(user, **staff_data)

    def update_staff(self, pk, data: dict):
        staff = self.get_staff(pk)
        return self.repo.update(staff, **data)

    def delete_staff(self, pk):
        self.repo.delete(self.get_staff(pk))
