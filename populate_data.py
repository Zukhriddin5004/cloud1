import datetime
import os
import django
import random
from faker import Faker

# Django settings setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_project.settings')
django.setup()

from django.contrib.auth.models import User
from django.db import transaction
from main.models import Employee, Category, Product, Supplier, Inventory, Sale

fake = Faker()


def create_employees(n=50):
    print("Creating employees...")
    for _ in range(n):
        try:
            with transaction.atomic():
                username = fake.user_name()
                while User.objects.filter(username=username).exists():
                    username = fake.user_name()

                user = User.objects.create_user(
                    username=username,
                    email=fake.email(),
                    password='password123'
                )
                Employee.objects.create(
                    user=user,
                    name=fake.name(),
                    position=fake.job(),
                    phone=fake.phone_number(),
                    email=user.email
                )
        except Exception as e:
            print(f"Error creating employee: {str(e)}")


def create_categories():
    print("Creating categories...")
    categories = ['Men', 'Women', 'Kids', 'Accessories', 'Shoes']
    for name in categories:
        try:
            Category.objects.get_or_create(name=name)
        except Exception as e:
            print(f"Error creating category {name}: {str(e)}")


def create_suppliers(n=100):
    print("Creating suppliers...")
    for _ in range(n):
        try:
            Supplier.objects.create(
                name=fake.company(),
                contact_person=fake.name(),
                phone=fake.phone_number(),
                email=fake.company_email(),
                address=fake.address()
            )
        except Exception as e:
            print(f"Error creating supplier: {str(e)}")


def create_products(n=1000):
    print("Creating products...")
    categories = list(Category.objects.all())
    if not categories:
        print("No categories found. Please create categories first.")
        return

    for _ in range(n):
        try:
            Product.objects.create(
                name=fake.word().capitalize() + " " + fake.color_name(),
                category=random.choice(categories),
                size=random.choice(['S', 'M', 'L', 'XL', 'XXL']),
                color=fake.color_name(),
                price=round(random.uniform(10, 200), 2),
                stock_quantity=random.randint(0, 100)
            )
        except Exception as e:
            print(f"Error creating product: {str(e)}")


def create_inventories(n=2000):
    print("Creating inventories...")
    products = list(Product.objects.all())
    suppliers = list(Supplier.objects.all())

    if not products or not suppliers:
        print("No products or suppliers found. Please create them first.")
        return

    for _ in range(n):
        try:
            with transaction.atomic():
                product = random.choice(products)
                quantity = random.randint(1, 50)
                Inventory.objects.create(
                    product=product,
                    supplier=random.choice(suppliers),
                    quantity=quantity,
                    unit_price=product.price
                )
        except Exception as e:
            print(f"Error creating inventory: {str(e)}")

def create_sales(n=1000):  # sales sonini oshirdik
    print("Creating sales...")
    products = list(Product.objects.all())
    employees = list(Employee.objects.all())

    if not products or not employees:
        print("No products or employees found. Please create them first.")
        return

    for _ in range(n):
        try:
            with transaction.atomic():
                product = random.choice(products)
                if product.stock_quantity > 0:
                    # quantity ni kamaytirdik: 1 yoki 2
                    quantity = random.randint(1, min(2, product.stock_quantity))
                    # employee lar orasidan random tanlash (har safar alohida)
                    employee = random.choice(employees)
                    Sale.objects.create(
                        product=product,
                        employee=employee,
                        quantity=quantity,
                        price=product.price
                    )
                    # stock ni yangilash
                    product.stock_quantity -= quantity
                    product.save()
        except Exception as e:
            print(f"Error creating sale: {str(e)}")


def main():
    print("Starting to generate fake data...")
    try:
        create_employees()
        create_categories()
        create_suppliers()
        create_products()
        create_inventories()
        create_sales()
        print("Successfully generated all fake data!")
    except Exception as e:
        print(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main()
