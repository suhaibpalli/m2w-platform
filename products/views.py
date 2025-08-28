from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from .models import Product, Category
from .forms import ProductForm, ProductSearchForm
from core.models import Industry
import json

# ─── Insert these two right here ──────────────────────────────
class BusinessBuyerRequiredMixin:
    """Only allow business‑buyer users."""
    def dispatch(self, request, *args, **kwargs):
        if request.user.company.role != 'business_buyer':
            raise PermissionDenied("Only business buyers may access this page.")
        return super().dispatch(request, *args, **kwargs)

class SubscriptionRequiredMixin:
    """Only allow users whose Company.subscription_status == 'active'."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.company.is_subscription_active:
            messages.error(request, "Your subscription is not active. Please renew to continue.")
            return redirect('core:pricing')
        return super().dispatch(request, *args, **kwargs)
# ───────────────────────────────────────────────────────────────

class VendorRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.company.role != 'vendor':
            raise PermissionDenied("Only vendors may manage products.")
        return super().dispatch(request, *args, **kwargs)

class ProductListView(ListView):
    """Public product listing with search and filters"""
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Product.objects.filter(status='active').select_related('company', 'category__industry')
        
        # Search functionality
        query = self.request.GET.get('query')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(tags__icontains=query)
            )
        
        # Category filter
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
            
        # Industry filter
        industry_id = self.request.GET.get('industry')
        if industry_id:
            queryset = queryset.filter(category__industry_id=industry_id)
        
        # Price range
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = ProductSearchForm(self.request.GET)
        context['industries'] = Industry.objects.filter(is_active=True)
        context['categories'] = Category.objects.filter(is_active=True).select_related('industry')
        return context

class ProductDetailView(DetailView):
    """Product detail view"""
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'
    
    def get_queryset(self):
        return Product.objects.filter(status='active').select_related('company', 'category__industry')
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Increment view count
        obj.increment_views()
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get related products from same category
        context['related_products'] = Product.objects.filter(
            category=self.object.category,
            status='active'
        ).exclude(pk=self.object.pk)[:6]
        
        # Get other products from same company
        context['company_products'] = Product.objects.filter(
            company=self.object.company,
            status='active'
        ).exclude(pk=self.object.pk)[:3]
        
        return context

class MyProductsView(
    VendorRequiredMixin,
    SubscriptionRequiredMixin,
    LoginRequiredMixin,
    ListView
):
    """Dashboard view for user's products"""
    model = Product
    template_name = 'products/my_products.html'
    context_object_name = 'products'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Product.objects.filter(
            company=self.request.user.company
        ).select_related('category')
        
        # Search in user's products
        query = self.request.GET.get('query')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )
            
        return queryset

class ProductCreateView(
    VendorRequiredMixin,
    SubscriptionRequiredMixin,
    LoginRequiredMixin,
    CreateView
):
    """Create new product"""
    model = Product
    form_class = ProductForm
    template_name = 'products/product_form.html'
    
    def form_valid(self, form):
        form.instance.company = self.request.user.company
        
        # Handle image uploads
        images = self.request.FILES.getlist('images')
        if images:
            form.instance.images = []
            for image in images[:3]:  # Limit to 3 images
                form.instance.add_image(image)
        
        # Check if saving as draft or publishing
        if 'save_draft' in self.request.POST:
            form.instance.status = 'draft'
            messages.success(self.request, 'Product saved as draft.')
        else:
            form.instance.status = 'active'
            messages.success(self.request, 'Product published successfully!')
            
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('products:my_products')

class ProductUpdateView(
    VendorRequiredMixin,
    SubscriptionRequiredMixin,
    LoginRequiredMixin,
    UpdateView
):
    """Edit existing product"""
    model = Product
    form_class = ProductForm
    template_name = 'products/product_form.html'
    
    def get_queryset(self):
        return Product.objects.filter(company=self.request.user.company)
    
    def form_valid(self, form):
        # Get the instance from the form without saving to the database yet.
        self.object = form.save(commit=False)

        # Handle image removal using data from the validated form.
        remove_images_raw = form.cleaned_data.get('remove_images', '') or ''
        image_urls_to_remove = []

        if remove_images_raw:
            # Expect JSON array from the form (e.g. '["data:...","data:..."]')
            try:
                image_urls_to_remove = json.loads(remove_images_raw)
                # ensure it's a list of strings
                if not isinstance(image_urls_to_remove, list):
                    image_urls_to_remove = []
            except Exception:
                # Fallback for older values: attempt comma split (best-effort)
                image_urls_to_remove = [url.strip() for url in remove_images_raw.split(',') if url.strip()]

        # Remove each URL from the instance's images list (uses your model helper)
        for image_url in image_urls_to_remove:
            self.object.remove_image(image_url)

        # Handle new image uploads from the request.
        new_images = self.request.FILES.getlist('images')
        if new_images:
            self.object.add_images(new_images)

        # Determine the product's status based on which submit button was clicked.
        if 'save_draft' in self.request.POST:
            self.object.status = 'draft'
            messages.success(self.request, 'Product updated and saved as draft.')
        else:
            self.object.status = 'active'
            messages.success(self.request, 'Product updated and published!')

        # Now, perform the final save of the fully modified object.
        self.object.save()

        # Redirect to the success URL, bypassing the problematic super() call.
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse_lazy('products:my_products')

class ProductDeleteView(
    VendorRequiredMixin,
    SubscriptionRequiredMixin,
    LoginRequiredMixin,
    DeleteView
):
    """Delete product"""
    model = Product
    template_name = 'products/product_confirm_delete.html'
    success_url = reverse_lazy('products:my_products')
    
    def get_queryset(self):
        return Product.objects.filter(company=self.request.user.company)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Product deleted successfully.')
        return super().delete(request, *args, **kwargs)

# Category views
class CategoryProductsView(ListView):
    """Products in a specific category"""
    model = Product
    template_name = 'products/category_products.html'
    context_object_name = 'products'
    paginate_by = 12
    
    def get_queryset(self):
        self.category = get_object_or_404(Category, pk=self.kwargs['category_id'], is_active=True)
        return Product.objects.filter(
            category=self.category,
            status='active'
        ).select_related('company')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context
