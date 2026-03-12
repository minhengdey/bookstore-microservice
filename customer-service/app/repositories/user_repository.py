from app.models import User


class UserRepository:
    def get_all(self):
        return User.objects.all()

    def get_by_id(self, user_id: int):
        return User.objects.filter(pk=user_id).first()

    def get_by_email(self, email: str):
        return User.objects.filter(email=email).first()

    def get_by_username(self, username: str):
        return User.objects.filter(username=username).first()

    def create(self, **kwargs) -> User:
        return User.objects.create(**kwargs)

    def update(self, user: User, **kwargs) -> User:
        for field, value in kwargs.items():
            setattr(user, field, value)
        user.save()
        return user

    def delete(self, user: User) -> None:
        user.delete()
