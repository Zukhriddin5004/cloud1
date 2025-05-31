from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.utils import timezone
import csv
import json
from decimal import Decimal
import datetime
from .models import Product, Category, Sale, Inventory, Employee, Supplier

def index(request):
    """Redirect to dashboard or login page"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    else:
        return redirect('login')

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


@login_required
def dashboard(request):
    """Display the main dashboard with key metrics and charts"""
    # Get summary statistics
    total_sales_amount = Sale.objects.aggregate(Sum('price'))['price__sum'] or 0
    total_products = Product.objects.count()
    low_stock_count = Product.objects.filter(stock_quantity__lt=10).count()
    total_employees = Employee.objects.count()
    
    # Get recent sales
    recent_sales = Sale.objects.select_related('product', 'employee').order_by('-date_time')[:10]
    
    # Get low stock products
    low_stock_products = Product.objects.select_related('category').filter(stock_quantity__lt=10).order_by('stock_quantity')
    
    # Prepare sales chart data (last 30 days)
    today = timezone.now().date()
    thirty_days_ago = today - datetime.timedelta(days=30)
    
    sales_data = []
    sales_dates = []
    
    for i in range(30):
        date = thirty_days_ago + datetime.timedelta(days=i)
        day_sales = Sale.objects.filter(date_time__date=date).aggregate(Sum('price'))['price__sum'] or 0
        sales_data.append(day_sales)
        sales_dates.append(date.strftime('%b %d'))
    
    # Prepare category chart data
    categories = Category.objects.all()
    category_names = []
    category_data = []
    
    for category in categories:
        category_names.append(category.name)
        category_sales = Sale.objects.filter(product__category=category).count()
        category_data.append(category_sales)
    
    context = {
        'total_sales_amount': total_sales_amount,
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'total_employees': total_employees,
        'recent_sales': recent_sales,
        'low_stock_products': low_stock_products,
        'sales_data': json.dumps(sales_data, default=decimal_default),
        'sales_dates': json.dumps(sales_dates),
        'category_names': json.dumps(category_names),
        'category_data': json.dumps(category_data),
    }
    
    return render(request, 'main/dashboard.html', context)

@login_required
def products(request):
    """Display and manage products"""
    # Get filter parameters
    category_id = request.GET.get('category')
    stock_status = request.GET.get('stock')
    
    # Apply filters
    products_list = Product.objects.select_related('category').all()
    
    if category_id:
        products_list = products_list.filter(category_id=category_id)
    
    if stock_status:
        if stock_status == 'in_stock':
            products_list = products_list.filter(stock_quantity__gt=10)
        elif stock_status == 'low_stock':
            products_list = products_list.filter(stock_quantity__gt=0, stock_quantity__lt=10)
        elif stock_status == 'out_of_stock':
            products_list = products_list.filter(stock_quantity=0)
    
    # Paginate results
    paginator = Paginator(products_list.order_by('name'), 10)
    page = request.GET.get('page', 1)
    products = paginator.get_page(page)
    
    # Get all categories for filter dropdown
    categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
    }
    
    return render(request, 'main/products.html', context)

@login_required
def add_product(request):
    """Add a new product"""
    if request.method == 'POST':
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        size = request.POST.get('size')
        color = request.POST.get('color')
        price = request.POST.get('price')
        stock_quantity = request.POST.get('stock_quantity')
        
        product = Product(
            name=name,
            category_id=category_id,
            size=size,
            color=color,
            price=price,
            stock_quantity=stock_quantity
        )
        product.save()
        
        return redirect('products')
    
    # If GET request, handled by products view
    return redirect('products')

@login_required
def edit_product(request, product_id):
    """Edit an existing product"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.category_id = request.POST.get('category')
        product.size = request.POST.get('size')
        product.color = request.POST.get('color')
        product.price = request.POST.get('price')
        product.stock_quantity = request.POST.get('stock_quantity')
        product.save()
        
        return redirect('products')
    
    categories = Category.objects.all()
    
    context = {
        'product': product,
        'categories': categories,
    }
    
    return render(request, 'main/edit_product.html', context)

@login_required
def delete_product(request, product_id):
    """Delete a product"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        product.delete()
        return redirect('products')
    
    context = {
        'product': product,
    }
    
    return render(request, 'main/delete_product.html', context)

@login_required
def sales(request):
    """Display and manage sales"""
    # Get filter parameters
    date_range = request.GET.get('date_range')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    employee_id = request.GET.get('employee')
    category_id = request.GET.get('category')
    
    # Apply filters
    sales_list = Sale.objects.select_related('product', 'employee', 'product__category').all()
    
    if date_range:
        today = timezone.now().date()
        if date_range == 'today':
            sales_list = sales_list.filter(date_time__date=today)
        elif date_range == 'yesterday':
            yesterday = today - datetime.timedelta(days=1)
            sales_list = sales_list.filter(date_time__date=yesterday)
        elif date_range == 'this_week':
            start_of_week = today - datetime.timedelta(days=today.weekday())
            sales_list = sales_list.filter(date_time__date__gte=start_of_week)
        elif date_range == 'last_week':
            start_of_last_week = today - datetime.timedelta(days=today.weekday() + 7)
            end_of_last_week = start_of_last_week + datetime.timedelta(days=6)
            sales_list = sales_list.filter(date_time__date__gte=start_of_last_week, date_time__date__lte=end_of_last_week)
        elif date_range == 'this_month':
            sales_list = sales_list.filter(date_time__month=today.month, date_time__year=today.year)
        elif date_range == 'last_month':
            last_month = today.month - 1 if today.month > 1 else 12
            year = today.year if today.month > 1 else today.year - 1
            sales_list = sales_list.filter(date_time__month=last_month, date_time__year=year)
    
    if start_date and end_date:
        sales_list = sales_list.filter(date_time__date__gte=start_date, date_time__date__lte=end_date)
    
    if employee_id:
        sales_list = sales_list.filter(employee_id=employee_id)
    
    if category_id:
        sales_list = sales_list.filter(product__category_id=category_id)
    
    # Calculate totals
    total_sales = sales_list.count()
    total_revenue = sales_list.aggregate(Sum('price'))['price__sum'] or 0
    average_sale = total_revenue / total_sales if total_sales > 0 else 0
    
    # Add total_price to each sale
    for sale in sales_list:
        sale.total_price = sale.price * sale.quantity
    
    # Paginate results
    paginator = Paginator(sales_list.order_by('-date_time'), 10)
    page = request.GET.get('page', 1)
    sales = paginator.get_page(page)
    
    # Get all employees and categories for filter dropdowns
    employees = Employee.objects.all()
    categories = Category.objects.all()
    all_products = Product.objects.filter(stock_quantity__gt=0)
    
    context = {
        'sales': sales,
        'employees': employees,
        'categories': categories,
        'all_products': all_products,
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'average_sale': average_sale,
    }
    
    return render(request, 'main/sales.html', context)

@login_required
def add_sale(request):
    """Add a new sale"""
    if request.method == 'POST':
        product_id = request.POST.get('product')
        employee_id = request.POST.get('employee')
        quantity = int(request.POST.get('quantity'))
        price = float(request.POST.get('price'))
        
        # Create the sale
        sale = Sale(
            product_id=product_id,
            employee_id=employee_id,
            quantity=quantity,
            price=price
        )
        sale.save()
        
        return redirect('sales')
    
    # If GET request, handled by sales view
    return redirect('sales')

@login_required
def view_sale(request, sale_id):
    """View details of a sale"""
    sale = get_object_or_404(Sale, id=sale_id)
    
    context = {
        'sale': sale,
    }
    
    return render(request, 'main/view_sale.html', context)

@login_required
def delete_sale(request, sale_id):
    """Delete a sale"""
    sale = get_object_or_404(Sale, id=sale_id)
    
    if request.method == 'POST':
        # Restore product stock quantity
        product = sale.product
        product.stock_quantity += sale.quantity
        product.save()
        
        sale.delete()
        return redirect('sales')
    
    context = {
        'sale': sale,
    }
    
    return render(request, 'main/delete_sale.html', context)

@login_required
def inventory(request):
    """Display and manage inventory"""
    # Get filter parameters
    supplier_id = request.GET.get('supplier')
    category_id = request.GET.get('category')
    date_range = request.GET.get('date_range')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Apply filters
    inventories_list = Inventory.objects.select_related('product', 'supplier', 'product__category').all()
    
    if supplier_id:
        inventories_list = inventories_list.filter(supplier_id=supplier_id)
    
    if category_id:
        inventories_list = inventories_list.filter(product__category_id=category_id)
    
    if date_range:
        today = timezone.now().date()
        if date_range == 'today':
            inventories_list = inventories_list.filter(date_received__date=today)
        elif date_range == 'this_week':
            start_of_week = today - datetime.timedelta(days=today.weekday())
            inventories_list = inventories_list.filter(date_received__date__gte=start_of_week)
        elif date_range == 'this_month':
            inventories_list = inventories_list.filter(date_received__month=today.month, date_received__year=today.year)
        elif date_range == 'last_month':
            last_month = today.month - 1 if today.month > 1 else 12
            year = today.year if today.month > 1 else today.year - 1
            inventories_list = inventories_list.filter(date_received__month=last_month, date_received__year=year)
    
    if start_date and end_date:
        inventories_list = inventories_list.filter(date_received__date__gte=start_date, date_received__date__lte=end_date)
    
    # Calculate totals
    total_products = inventories_list.values('product').distinct().count()
    total_items = inventories_list.aggregate(Sum('quantity'))['quantity__sum'] or 0
    total_value = 0
    
    # Add total_value to each inventory item
    for inventory in inventories_list:
        inventory.total_value = inventory.quantity * inventory.unit_price
        total_value += inventory.total_value
    
    # Paginate results
    paginator = Paginator(inventories_list.order_by('-date_received'), 10)
    page = request.GET.get('page', 1)
    inventories = paginator.get_page(page)
    
    # Get all suppliers, categories, and products for dropdowns
    suppliers = Supplier.objects.all()
    categories = Category.objects.all()
    all_products = Product.objects.all()
    
    context = {
        'inventories': inventories,
        'suppliers': suppliers,
        'categories': categories,
        'all_products': all_products,
        'total_products': total_products,
        'total_items': total_items,
        'total_value': total_value,
    }
    
    return render(request, 'main/inventory.html', context)

@login_required
def add_inventory(request):
    """Add new inventory"""
    if request.method == 'POST':
        product_id = request.POST.get('product')
        supplier_id = request.POST.get('supplier')
        quantity = int(request.POST.get('quantity'))
        unit_price = float(request.POST.get('unit_price'))
        
        # Create the inventory record
        inventory = Inventory(
            product_id=product_id,
            supplier_id=supplier_id,
            quantity=quantity,
            unit_price=unit_price
        )
        inventory.save()
        
        return redirect('inventory')
    
    # If GET request, handled by inventory view
    return redirect('inventory')

@login_required
def view_inventory(request, inventory_id):
    """View details of an inventory record"""
    inventory = get_object_or_404(Inventory, id=inventory_id)
    
    context = {
        'inventory': inventory,
    }
    
    return render(request, 'main/view_inventory.html', context)

@login_required
def delete_inventory(request, inventory_id):
    """Delete an inventory record"""
    inventory = get_object_or_404(Inventory, id=inventory_id)
    
    if request.method == 'POST':
        # Reduce product stock quantity
        product = inventory.product
        product.stock_quantity -= inventory.quantity
        product.save()
        
        inventory.delete()
        return redirect('inventory')
    
    context = {
        'inventory': inventory,
    }
    
    return render(request, 'main/delete_inventory.html', context)

@login_required
def employees(request):
    """Display and manage employees"""
    employees_list = Employee.objects.all()

    # Calculate sales performance for each employee
    max_sales = Sale.objects.values('employee').annotate(count=Count('id')).order_by('-count').first()
    max_count = max_sales['count'] if max_sales else 1

    for employee in employees_list:
        employee.sales_count = Sale.objects.filter(employee=employee).count()
        employee.performance_percentage = (employee.sales_count / max_count) * 100 if max_count > 0 else 0

    # Prepare chart data
    employee_names = []
    employee_sales = []

    for employee in employees_list:
        employee_names.append(employee.name)
        employee_sales.append(employee.sales_count)

    context = {
        'employees': employees_list,
        'employee_names': json.dumps(employee_names),
        'employee_sales': json.dumps(employee_sales),
    }

    return render(request, 'main/employees.html', context)

@login_required
def add_employee(request):
    """Add a new employee"""
    if request.method == 'POST':
        name = request.POST.get('name')
        position = request.POST.get('position')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        create_user = request.POST.get('create_user') == 'on'

        # Create the employee
        employee = Employee(
            name=name,
            position=position,
            phone=phone,
            email=email
        )

        # Create user account if requested
        if create_user:
            username = request.POST.get('username')
            password = request.POST.get('password')

            user = User.objects.create_user(username=username, email=email, password=password)
            employee.user = user

        employee.save()

        return redirect('employees')

    # If GET request, handled by employees view
    return redirect('employees')

@login_required
def employee_detail(request, employee_id):
    """View employee details and performance"""
    employee = get_object_or_404(Employee, id=employee_id)

    # Get employee sales
    sales = Sale.objects.filter(employee=employee).select_related('product').order_by('-date_time')

    # Calculate statistics
    total_sales = sales.count()
    total_revenue = sales.aggregate(Sum('price'))['price__sum'] or 0

    # Prepare monthly sales data for chart
    today = timezone.now().date()
    months_data = []
    months_labels = []

    for i in range(6):
        month = today.month - i if today.month > i else 12 - (i - today.month)
        year = today.year if today.month > i else today.year - 1

        month_sales = Sale.objects.filter(
            employee=employee,
            date_time__month=month,
            date_time__year=year
        ).aggregate(Sum('price'))['price__sum'] or 0

        month_name = datetime.date(year, month, 1).strftime('%b %Y')
        months_data.append(month_sales)
        months_labels.append(month_name)

    # Reverse lists to show chronological order
    months_data.reverse()
    months_labels.reverse()

    context = {
        'employee': employee,
        'sales': sales[:10],  # Show only the 10 most recent sales
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'months_data': json.dumps(months_data, default=decimal_default),
        'months_labels': json.dumps(months_labels),
    }

    return render(request, 'main/employee_detail.html', context)

@login_required
def edit_employee(request, employee_id):
    """Edit an existing employee"""
    employee = get_object_or_404(Employee, id=employee_id)
    
    if request.method == 'POST':
        employee.name = request.POST.get('name')
        employee.position = request.POST.get('position')
        employee.phone = request.POST.get('phone')
        employee.email = request.POST.get('email')
        
        # Update user account if it exists
        if employee.user:
            employee.user.email = request.POST.get('email')
            
            # Update password if provided
            new_password = request.POST.get('new_password')
            if new_password:
                employee.user.set_password(new_password)
            
            employee.user.save()
        
        employee.save()
        
        return redirect('employees')
    
    context = {
        'employee': employee,
    }
    
    return render(request, 'main/edit_employee.html', context)

@login_required
def delete_employee(request, employee_id):
    """Delete an employee"""
    employee = get_object_or_404(Employee, id=employee_id)
    
    if request.method == 'POST':
        # Delete associated user if it exists
        if employee.user:
            employee.user.delete()
        
        employee.delete()
        return redirect('employees')
    
    context = {
        'employee': employee,
    }
    
    return render(request, 'main/delete_employee.html', context)

@login_required
def reports(request):
    """Generate and display reports"""
    # Get report type
    report_type = request.GET.get('type', 'sales')
    
    context = {
        'report_type': report_type,
    }
    
    if report_type == 'sales':
        # Sales report
        sales_data = Sale.objects.select_related('product', 'employee').order_by('-date_time')
        context['sales_data'] = sales_data
        
    elif report_type == 'inventory':
        # Inventory report
        inventory_data = Product.objects.select_related('category').all()
        context['inventory_data'] = inventory_data
        
    elif report_type == 'employee':
        # Employee performance report
        employees_data = Employee.objects.all()
        
        for employee in employees_data:
            employee.sales_count = Sale.objects.filter(employee=employee).count()
            employee.sales_revenue = Sale.objects.filter(employee=employee).aggregate(Sum('price'))['price__sum'] or 0
        
        context['employees_data'] = employees_data
    
    return render(request, 'main/reports.html', context)

@login_required
def settings(request):
    """User and system settings"""
    if request.method == 'POST':
        # Handle settings update
        pass
    
    return render(request, 'main/settings.html')

@login_required
def search(request):
    """Search functionality"""
    query = request.GET.get('q', '')
    results = {}
    
    if query:
        # Search products
        products = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(category__name__icontains=query)
        ).select_related('category')
        results['products'] = products
        
        # Search employees
        employees = Employee.objects.filter(
            Q(name__icontains=query) | 
            Q(position__icontains=query) | 
            Q(email__icontains=query)
        )
        results['employees'] = employees
        
        # Search suppliers
        suppliers = Supplier.objects.filter(
            Q(name__icontains=query) | 
            Q(contact_person__icontains=query) | 
            Q(email__icontains=query)
        )
        results['suppliers'] = suppliers
    
    context = {
        'query': query,
        'results': results,
    }
    
    return render(request, 'main/search_results.html', context)

@login_required
def export_products(request):
    """Export products to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="products.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Name', 'Category', 'Size', 'Color', 'Price', 'Stock Quantity'])
    
    products = Product.objects.select_related('category').all()
    
    for product in products:
        writer.writerow([
            product.name,
            product.category.name,
            product.size or '',
            product.color or '',
            product.price,
            product.stock_quantity
        ])
    
    return response

@login_required
def export_sales(request):
    """Export sales to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sales.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Product', 'Category', 'Employee', 'Date', 'Quantity', 'Price', 'Total'])
    
    # Apply the same filters as in the sales view
    date_range = request.GET.get('date_range')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    employee_id = request.GET.get('employee')
    category_id = request.GET.get('category')
    
    sales = Sale.objects.select_related('product', 'employee', 'product__category').all()
    
    if date_range:
        today = timezone.now().date()
        if date_range == 'today':
            sales = sales.filter(date_time__date=today)
        elif date_range == 'yesterday':
            yesterday = today - datetime.timedelta(days=1)
            sales = sales.filter(date_time__date=yesterday)
        elif date_range == 'this_week':
            start_of_week = today - datetime.timedelta(days=today.weekday())
            sales = sales.filter(date_time__date__gte=start_of_week)
        elif date_range == 'last_week':
            start_of_last_week = today - datetime.timedelta(days=today.weekday() + 7)
            end_of_last_week = start_of_last_week + datetime.timedelta(days=6)
            sales = sales.filter(date_time__date__gte=start_of_last_week, date_time__date__lte=end_of_last_week)
        elif date_range == 'this_month':
            sales = sales.filter(date_time__month=today.month, date_time__year=today.year)
        elif date_range == 'last_month':
            last_month = today.month - 1 if today.month > 1 else 12
            year = today.year if today.month > 1 else today.year - 1
            sales = sales.filter(date_time__month=last_month, date_time__year=year)
    
    if start_date and end_date:
        sales = sales.filter(date_time__date__gte=start_date, date_time__date__lte=end_date)
    
    if employee_id:
        sales = sales.filter(employee_id=employee_id)
    
    if category_id:
        sales = sales.filter(product__category_id=category_id)
    
    for sale in sales:
        writer.writerow([
            sale.product.name,
            sale.product.category.name,
            sale.employee.name,
            sale.date_time.strftime('%Y-%m-%d %H:%M'),
            sale.quantity,
            sale.price,
            sale.quantity * sale.price
        ])
    
    return response

@login_required
def export_inventory(request):
    """Export inventory to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Product', 'Category', 'Supplier', 'Quantity', 'Unit Price', 'Total Value', 'Date Received'])
    
    # Apply the same filters as in the inventory view
    supplier_id = request.GET.get('supplier')
    category_id = request.GET.get('category')
    date_range = request.GET.get('date_range')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    inventories = Inventory.objects.select_related('product', 'supplier', 'product__category').all()
    
    if supplier_id:
        inventories = inventories.filter(supplier_id=supplier_id)
    
    if category_id:
        inventories = inventories.filter(product__category_id=category_id)
    
    if date_range:
        today = timezone.now().date()
        if date_range == 'today':
            inventories = inventories.filter(date_received__date=today)
        elif date_range == 'this_week':
            start_of_week = today - datetime.timedelta(days=today.weekday())
            inventories = inventories.filter(date_received__date__gte=start_of_week)
        elif date_range == 'this_month':
            inventories = inventories.filter(date_received__month=today.month, date_received__year=today.year)
        elif date_range == 'last_month':
            last_month = today.month - 1 if today.month > 1 else 12
            year = today.year if today.month > 1 else today.year - 1
            inventories = inventories.filter(date_received__month=last_month, date_received__year=year)
    
    if start_date and end_date:
        inventories = inventories.filter(date_received__date__gte=start_date, date_received__date__lte=end_date)
    
    for inventory in inventories:
        writer.writerow([
            inventory.product.name,
            inventory.product.category.name,
            inventory.supplier.name,
            inventory.quantity,
            inventory.unit_price,
            inventory.quantity * inventory.unit_price,
            inventory.date_received.strftime('%Y-%m-%d %H:%M')
        ])
    
    return response

@login_required
def export_employees(request):
    """Export employees to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="employees.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Name', 'Position', 'Phone', 'Email', 'Date Joined', 'Sales Count', 'Sales Revenue'])
    
    employees = Employee.objects.all()
    
    for employee in employees:
        sales_count = Sale.objects.filter(employee=employee).count()
        sales_revenue = Sale.objects.filter(employee=employee).aggregate(Sum('price'))['price__sum'] or 0
        
        writer.writerow([
            employee.name,
            employee.position,
            employee.phone,
            employee.email,
            employee.date_joined.strftime('%Y-%m-%d'),
            sales_count,
            sales_revenue
        ])
    
    return response

@login_required
def api_sales_data(request):
    """API endpoint for sales chart data"""
    period = request.GET.get('period', 'daily')
    today = timezone.now().date()
    
    labels = []
    values = []
    
    if period == 'daily':
        # Daily data for the last 30 days
        thirty_days_ago = today - datetime.timedelta(days=30)
        
        for i in range(30):
            date = thirty_days_ago + datetime.timedelta(days=i)
            day_sales = Sale.objects.filter(date_time__date=date).aggregate(Sum('price'))['price__sum'] or 0
            labels.append(date.strftime('%b %d'))
            values.append(day_sales)
    
    elif period == 'weekly':
        # Weekly data for the last 12 weeks
        for i in range(12):
            end_date = today - datetime.timedelta(days=i * 7)
            start_date = end_date - datetime.timedelta(days=6)
            week_sales = Sale.objects.filter(date_time__date__range=[start_date, end_date]).aggregate(Sum('price'))['price__sum'] or 0
            labels.append(f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}")
            values.append(week_sales)
        
        # Reverse to show chronological order
        labels.reverse()
        values.reverse()
    
    elif period == 'monthly':
        # Monthly data for the last 12 months
        for i in range(12):
            month = today.month - i if today.month > i else 12 - (i - today.month)
            year = today.year if today.month > i else today.year - 1
            
            month_sales = Sale.objects.filter(date_time__month=month, date_time__year=year).aggregate(Sum('price'))['price__sum'] or 0
            month_name = datetime.date(year, month, 1).strftime('%b %Y')
            labels.append(month_name)
            values.append(month_sales)
        
        # Reverse to show chronological order
        labels.reverse()
        values.reverse()
    
    return JsonResponse({
        'labels': labels,
        'values': values
    })

@login_required
def api_employee_performance(request):
    """API endpoint for employee performance chart data"""
    period = request.GET.get('period', 'this_month')
    today = timezone.now().date()
    
    # Filter sales based on period
    sales_query = Sale.objects.all()
    
    if period == 'this_month':
        sales_query = sales_query.filter(date_time__month=today.month, date_time__year=today.year)
    elif period == 'last_month':
        last_month = today.month - 1 if today.month > 1 else 12
        year = today.year if today.month > 1 else today.year - 1
        sales_query = sales_query.filter(date_time__month=last_month, date_time__year=year)
    elif period == 'this_year':
        sales_query = sales_query.filter(date_time__year=today.year)
    
    # Get employee performance data
    employees = Employee.objects.all()
    labels = []
    values = []
    
    for employee in employees:
        labels.append(employee.name)
        values.append(sales_query.filter(employee=employee).count())
    
    return JsonResponse({
        'labels': labels,
        'values': values
    })

def login_view(request):
    """User login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            error_message = "Invalid username or password"
            return render(request, 'main/login.html', {'error_message': error_message})
    
    return render(request, 'main/login.html')

@login_required
def logout_view(request):
    """User logout"""
    logout(request)
    return redirect('login')
