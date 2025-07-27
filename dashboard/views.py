from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from accounts.models import Company
from products.models import Product
from core.models import Industry
from django.contrib.auth.models import User

class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard_home.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Check subscription status before allowing access"""
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        company = request.user.company
        # Remove this overly restrictive check - allow pending users to see dashboard
        # if company.subscription_status != 'active':
        #     return redirect('accounts:profile')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        company = user.company
        
        # Role-based dashboard content
        if company.role == 'vendor':
            context.update(self.get_vendor_context(company))
        elif company.role == 'business_buyer':
            context.update(self.get_buyer_context(company))
        else:  # consumer_buyer
            context.update(self.get_consumer_buyer_context(company))
            
        # Common context
        context['user'] = user
        context['company'] = company
        context['is_vendor'] = company.role == 'vendor'
        context['is_business_buyer'] = company.role == 'business_buyer'
        context['is_consumer_buyer'] = company.role == 'consumer_buyer'
        
        return context
    
    def get_vendor_context(self, company):
        """Context for vendor dashboard"""
        # Get vendor's products
        products = Product.objects.filter(company=company)
        recent_products = products.order_by('-created_at')[:5]
        
        # Analytics
        total_products = products.count()
        active_products = products.filter(status='active').count()
        draft_products = products.filter(status='draft').count()
        total_views = sum(product.views_count for product in products if hasattr(product, 'views_count'))
        
        # Recent activity (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_activity = []
        
        # Add recent products to activity
        for product in products.filter(created_at__gte=thirty_days_ago)[:10]:
            recent_activity.append({
                'type': 'product_added',
                'description': f'Product "{product.name}" was added',
                'timestamp': product.created_at,
                'details': f'Category: {product.category.name}'
            })
        
        recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return {
            'total_products': total_products,
            'active_products': active_products,
            'draft_products': draft_products,
            'total_views': total_views,
            'recent_products': recent_products,
            'recent_activity': recent_activity[:10],
            'subscription_status': company.subscription_status,
            'subscription_expiry': company.subscription_end_date,
        }
    
    def get_buyer_context(self, company):
        """Context for buyer dashboard"""
        # For buyers - show marketplace stats and saved items
        total_products = Product.objects.filter(status='active').count()
        industries = Industry.objects.filter(is_active=True)
        
        # Recent marketplace activity
        recent_products = Product.objects.filter(status='active').order_by('-created_at')[:10]
        recent_activity = []
        
        for product in recent_products:
            recent_activity.append({
                'type': 'new_product',
                'description': f'New product "{product.name}" available',
                'timestamp': product.created_at,
                'details': f'By {product.company.company_name}'
            })
        
        return {
            'total_marketplace_products': total_products,
            'available_industries': industries.count(),
            'recent_marketplace_products': recent_products[:5],
            'recent_activity': recent_activity,
        }
    
    def get_consumer_buyer_context(self, company):
        """Context for consumer buyer dashboard"""
        # Similar to business buyer but with consumer-specific features
        total_products = Product.objects.filter(status='active').count()
        industries = Industry.objects.filter(is_active=True)
        
        # Recent marketplace activity
        recent_products = Product.objects.filter(status='active').order_by('-created_at')[:10]
        recent_activity = []
        
        for product in recent_products:
            recent_activity.append({
                'type': 'new_product',
                'description': f'New product "{product.name}" available',
                'timestamp': product.created_at,
                'details': f'By {product.company.company_name}'
            })
        
        return {
            'total_marketplace_products': total_products,
            'available_industries': industries.count(),
            'recent_marketplace_products': recent_products[:5],
            'recent_activity': recent_activity,
        }

class AdminDashboardView(LoginRequiredMixin, TemplateView):
    """Admin-only dashboard view"""
    template_name = 'dashboard/admin_dashboard.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Key metrics
        total_users = User.objects.count()
        total_companies = Company.objects.count()
        total_products = Product.objects.count()
        active_subscriptions = Company.objects.filter(subscription_status='active').count()
        
        # Growth metrics (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        new_users_30d = User.objects.filter(date_joined__gte=thirty_days_ago).count()
        new_products_30d = Product.objects.filter(created_at__gte=thirty_days_ago).count()
        
        # Industry distribution
        industry_stats = []
        for industry in Industry.objects.filter(is_active=True):
            product_count = Product.objects.filter(category__industry=industry).count()
            industry_stats.append({
                'name': industry.name,
                'count': product_count,
                'percentage': (product_count / total_products * 100) if total_products > 0 else 0
            })
        
        # Recent activity
        recent_activity = []
        
        # Recent registrations
        recent_users = User.objects.order_by('-date_joined')[:5]
        for user in recent_users:
            recent_activity.append({
                'type': 'New Registration',
                'description': f'{user.company.company_name} registered',
                'timestamp': user.date_joined
            })
        
        # Recent products
        recent_products = Product.objects.order_by('-created_at')[:5]
        for product in recent_products:
            recent_activity.append({
                'type': 'New Product',
                'description': f'{product.name} added by {product.company.company_name}',
                'timestamp': product.created_at
            })
        
        # Sort by timestamp
        recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
        
        context.update({
            'total_users': total_users,
            'total_companies': total_companies,
            'total_products': total_products,
            'active_subscriptions': active_subscriptions,
            'new_users_30d': new_users_30d,
            'new_products_30d': new_products_30d,
            'user_growth_rate': (new_users_30d / total_users * 100) if total_users > 0 else 0,
            'product_growth_rate': (new_products_30d / total_products * 100) if total_products > 0 else 0,
            'industry_stats': industry_stats,
            'recent_activity': recent_activity[:10],
        })
        
        return context
