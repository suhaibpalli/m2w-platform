from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib import messages
from .models import Industry, ContactInquiry, SiteSettings, HeroCarouselImage, TestimonialCarousel
from .forms import ContactForm

class HomeView(TemplateView):
    template_name = 'core/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['industries'] = Industry.objects.filter(is_active=True)
        context['hero_images'] = HeroCarouselImage.objects.filter(is_active=True)
        context['testimonials'] = TestimonialCarousel.objects.filter(is_active=True)
        # site_settings is now global, so we don't set it here
        return context

class AboutView(TemplateView):
    template_name = 'core/about.html'

class IndustriesView(TemplateView):
    template_name = 'core/industries.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['industries'] = Industry.objects.filter(is_active=True)
        
        # Get categories grouped by industry for the detailed sections
        from products.models import Category, Product
        from accounts.models import Company
        from django.db.models import Count, Q
        
        context['industry_categories'] = {}
        context['industry_stats'] = {}
        
        for industry in context['industries']:
            # Get categories for this industry
            categories = Category.objects.filter(
                industry=industry,
                is_active=True,
                parent=None  # Only parent categories
            ).prefetch_related('subcategories')
            context['industry_categories'][industry.slug] = categories
            
            # Calculate real statistics for this industry
            # Get all categories (including subcategories) for this industry
            all_categories = Category.objects.filter(
                industry=industry,
                is_active=True
            )
            
            # Count products in this industry
            total_products = Product.objects.filter(
                category__industry=industry,
                status='active'
            ).count()
            
            # Count unique suppliers in this industry
            active_suppliers = Company.objects.filter(
                products__category__industry=industry,
                products__status='active'
            ).distinct().count()
            
            # Count active categories
            active_categories = all_categories.count()
            
            context['industry_stats'][industry.slug] = {
                'active_categories': active_categories,
                'total_products': total_products,
                'active_suppliers': active_suppliers,
            }
            
        return context

class PricingView(TemplateView):
    template_name = 'core/pricing.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # site_settings is now global, so we don't set it here
        return context

class ContactView(TemplateView):
    template_name = 'core/contact.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ContactForm()
        return context
    
    def post(self, request, *args, **kwargs):
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thank you for your message! We will get back to you soon.')
            return redirect('core:contact')
        else:
            context = self.get_context_data(**kwargs)
            context['form'] = form
            return self.render_to_response(context)
