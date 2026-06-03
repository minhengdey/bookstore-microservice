from django.db import transaction, IntegrityError
from django.utils.text import slugify
from catalog.models import Category
from rest_framework.exceptions import ValidationError

class CategoryService:
    @staticmethod
    def generate_slug(name, counter=0):
        base_slug = slugify(name)
        if counter > 0:
            return f"{base_slug}-{counter}"
        return base_slug

    @staticmethod
    def compute_path_and_level(category):
        if category.parent:
            category.level = category.parent.level + 1
            category.full_path = f"{category.parent.full_path}/{category.slug}"
        else:
            category.level = 1
            category.full_path = category.slug

    @staticmethod
    def _check_cycle(category, new_parent):
        if not new_parent:
            return
        if category.id == new_parent.id:
            raise ValidationError("A category cannot be its own parent.")
        
        # Check if new_parent is a descendant of category
        current = new_parent
        while current.parent_id:
            if current.parent_id == category.id:
                raise ValidationError("Cycle detected: Cannot set a descendant as parent.")
            current = current.parent

    @staticmethod
    def create_category(name, parent_id=None):
        parent = Category.objects.get(id=parent_id) if parent_id else None
        
        counter = 0
        while True:
            slug = CategoryService.generate_slug(name, counter)
            category = Category(name=name, parent=parent, slug=slug)
            CategoryService.compute_path_and_level(category)
            
            try:
                with transaction.atomic():
                    category.save()
                return category
            except IntegrityError:
                # Slug collision, increment and retry
                counter += 1

    @staticmethod
    def update_category(category, name=None, parent_id=None):
        path_changed = False
        new_parent = None
        
        if parent_id is not None:
            new_parent = Category.objects.get(id=parent_id) if parent_id else None
            CategoryService._check_cycle(category, new_parent)
            
        counter = 0
        while True:
            try:
                with transaction.atomic():
                    if name and category.name != name:
                        category.name = name
                        category.slug = CategoryService.generate_slug(name, counter)
                        path_changed = True
                        
                    if parent_id is not None:
                        if category.parent != new_parent:
                            category.parent = new_parent
                            path_changed = True
                            
                    if path_changed:
                        CategoryService.compute_path_and_level(category)
                        category.save()
                        
                        # Cascade path changes to descendants
                        descendants = category.children.all()
                        if descendants:
                            CategoryService._cascade_update_descendants(category, descendants)
                    else:
                        category.save()
                        
                return category
            except IntegrityError:
                if name and category.name != name:
                    counter += 1
                else:
                    raise
        
    @staticmethod
    def _cascade_update_descendants(parent, children):
        # BFS traversal for cascading full_path and level updates
        queue = [(parent, list(children))]
        to_update = []
        
        while queue:
            current_parent, current_children = queue.pop(0)
            for child in current_children:
                child.level = current_parent.level + 1
                child.full_path = f"{current_parent.full_path}/{child.slug}"
                to_update.append(child)
                
                grandchildren = list(child.children.all())
                if grandchildren:
                    queue.append((child, grandchildren))
                    
        if to_update:
            Category.objects.bulk_update(to_update, ['level', 'full_path'])
