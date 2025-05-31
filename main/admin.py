from django.contrib import admin
from .models import Employee, Category, Product, Supplier, Inventory, Sale

# Register models with admin site
admin.site.register(Employee)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Supplier)
admin.site.register(Inventory)
admin.site.register(Sale)
