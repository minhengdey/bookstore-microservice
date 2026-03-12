from app.repositories import AuthorRepository, CategoryRepository, GenreRepository, PublisherRepository


class AuthorService:
    def __init__(self): self.repo = AuthorRepository()
    def list(self, search=None):
        return self.repo.search(search) if search else self.repo.get_all()
    def get(self, pk):
        obj = self.repo.get_by_id(pk)
        if not obj: raise ValueError(f"Author {pk} not found")
        return obj
    def create(self, data): return self.repo.create(**data)
    def update(self, pk, data): return self.repo.update(self.get(pk), **data)
    def delete(self, pk): self.repo.delete(self.get(pk))


class CategoryService:
    def __init__(self): self.repo = CategoryRepository()
    def list(self): return self.repo.get_all()
    def get(self, pk):
        obj = self.repo.get_by_id(pk)
        if not obj: raise ValueError(f"Category {pk} not found")
        return obj
    def create(self, data): return self.repo.create(**data)
    def update(self, pk, data): return self.repo.update(self.get(pk), **data)
    def delete(self, pk): self.repo.delete(self.get(pk))


class GenreService:
    def __init__(self): self.repo = GenreRepository()
    def list(self): return self.repo.get_all()
    def get(self, pk):
        obj = self.repo.get_by_id(pk)
        if not obj: raise ValueError(f"Genre {pk} not found")
        return obj
    def create(self, data): return self.repo.create(**data)
    def update(self, pk, data): return self.repo.update(self.get(pk), **data)
    def delete(self, pk): self.repo.delete(self.get(pk))


class PublisherService:
    def __init__(self): self.repo = PublisherRepository()
    def list(self): return self.repo.get_all()
    def get(self, pk):
        obj = self.repo.get_by_id(pk)
        if not obj: raise ValueError(f"Publisher {pk} not found")
        return obj
    def create(self, data): return self.repo.create(**data)
    def update(self, pk, data): return self.repo.update(self.get(pk), **data)
    def delete(self, pk): self.repo.delete(self.get(pk))
