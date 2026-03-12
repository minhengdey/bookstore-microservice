from app.models import Author, Category, Genre, Publisher


class AuthorRepository:
    def get_all(self): return Author.objects.all()
    def get_by_id(self, pk): return Author.objects.filter(pk=pk).first()
    def search(self, name): return Author.objects.filter(author_name__icontains=name)
    def create(self, **kw): return Author.objects.create(**kw)
    def update(self, obj, **kw):
        for k, v in kw.items(): setattr(obj, k, v)
        obj.save(); return obj
    def delete(self, obj): obj.delete()


class CategoryRepository:
    def get_all(self): return Category.objects.all()
    def get_by_id(self, pk): return Category.objects.filter(pk=pk).first()
    def get_roots(self): return Category.objects.filter(parent_category=None)
    def create(self, **kw): return Category.objects.create(**kw)
    def update(self, obj, **kw):
        for k, v in kw.items(): setattr(obj, k, v)
        obj.save(); return obj
    def delete(self, obj): obj.delete()


class GenreRepository:
    def get_all(self): return Genre.objects.all()
    def get_by_id(self, pk): return Genre.objects.filter(pk=pk).first()
    def create(self, **kw): return Genre.objects.create(**kw)
    def update(self, obj, **kw):
        for k, v in kw.items(): setattr(obj, k, v)
        obj.save(); return obj
    def delete(self, obj): obj.delete()


class PublisherRepository:
    def get_all(self): return Publisher.objects.all()
    def get_by_id(self, pk): return Publisher.objects.filter(pk=pk).first()
    def create(self, **kw): return Publisher.objects.create(**kw)
    def update(self, obj, **kw):
        for k, v in kw.items(): setattr(obj, k, v)
        obj.save(); return obj
    def delete(self, obj): obj.delete()
