from django import forms
from django.utils.safestring import mark_safe
from .models import Product, Category
from core.models import Industry

class MultipleFileInput(forms.Widget):
    """Custom widget for multiple file uploads"""
    def __init__(self, attrs=None):
        default_attrs = {'multiple': 'multiple', 'type': 'file'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}
        attrs.update(self.attrs)
        attrs['name'] = name
        attrs['id'] = attrs.get('id', f'id_{name}')
        
        # Build the HTML attributes string
        attr_list = []
        for key, val in attrs.items():
            if val is not None:
                attr_list.append(f'{key}="{val}"')
        
        return mark_safe(f'<input {" ".join(attr_list)} />')

class ProductForm(forms.ModelForm):
    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#111518] focus:outline-0 focus:ring-0 border border-[#dbe1e6] bg-white focus:border-[#dbe1e6] h-14 placeholder:text-[#60768a] p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Enter tags separated by commas'
        })
    )
    
    images = forms.FileField(
        required=False,
        widget=MultipleFileInput(attrs={
            'accept': 'image/*',
            'class': 'hidden'
        })
    )
    
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'description', 'price', 'currency',
            'minimum_order_quantity', 'lead_time', 'tags'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#111518] focus:outline-0 focus:ring-0 border border-[#dbe1e6] bg-white focus:border-[#dbe1e6] h-14 placeholder:text-[#60768a] p-[15px] text-base font-normal leading-normal',
                'placeholder': 'Enter product name'
            }),
            'category': forms.Select(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#111518] focus:outline-0 focus:ring-0 border border-[#dbe1e6] bg-white focus:border-[#dbe1e6] h-14 bg-[image:--select-button-svg] placeholder:text-[#60768a] p-[15px] text-base font-normal leading-normal'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#111518] focus:outline-0 focus:ring-0 border border-[#dbe1e6] bg-white focus:border-[#dbe1e6] min-h-36 placeholder:text-[#60768a] p-[15px] text-base font-normal leading-normal',
                'placeholder': 'Enter product description'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#111518] focus:outline-0 focus:ring-0 border border-[#dbe1e6] bg-white focus:border-[#dbe1e6] h-14 placeholder:text-[#60768a] p-[15px] text-base font-normal leading-normal',
                'placeholder': 'Enter price',
                'step': '0.01'
            }),
            'currency': forms.Select(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#111518] focus:outline-0 focus:ring-0 border border-[#dbe1e6] bg-white focus:border-[#dbe1e6] h-14 bg-[image:--select-button-svg] placeholder:text-[#60768a] p-[15px] text-base font-normal leading-normal'
            }, choices=[
                ('USD', 'USD'),
                ('EUR', 'EUR'),
                ('GBP', 'GBP'),
                ('INR', 'INR'),
            ]),
            'minimum_order_quantity': forms.TextInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#111518] focus:outline-0 focus:ring-0 border border-[#dbe1e6] bg-white focus:border-[#dbe1e6] h-14 placeholder:text-[#60768a] p-[15px] text-base font-normal leading-normal',
                'placeholder': 'e.g., 10 tons, 100 pieces'
            }),
            'lead_time': forms.TextInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#111518] focus:outline-0 focus:ring-0 border border-[#dbe1e6] bg-white focus:border-[#dbe1e6] h-14 placeholder:text-[#60768a] p-[15px] text-base font-normal leading-normal',
                'placeholder': 'e.g., 2-3 weeks, 30 days'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Group categories by industry
        self.fields['category'].queryset = Category.objects.filter(is_active=True).select_related('industry')
        
class ProductSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#111518] focus:outline-0 focus:ring-0 border-none bg-[#f0f2f5] focus:border-none h-full placeholder:text-[#60768a] px-4 rounded-l-none border-l-0 pl-2 text-base font-normal leading-normal',
            'placeholder': 'Search products...'
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-[#111518] focus:outline-0 focus:ring-0 border border-[#dbe1e6] bg-white focus:border-[#dbe1e6] h-14 bg-[image:--select-button-svg] placeholder:text-[#617689] p-[15px] text-base font-normal leading-normal'
        })
    )
    
    industry = forms.ModelChoiceField(
        queryset=Industry.objects.filter(is_active=True),
        required=False,
        empty_label="All Industries",
        widget=forms.Select(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-[#111518] focus:outline-0 focus:ring-0 border border-[#dbe1e6] bg-white focus:border-[#dbe1e6] h-14 bg-[image:--select-button-svg] placeholder:text-[#617689] p-[15px] text-base font-normal leading-normal'
        })
    )
    
    min_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-[#111518] focus:outline-0 focus:ring-0 border border-[#dbe1e6] bg-white focus:border-[#dbe1e6] h-14 placeholder:text-[#617689] p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Min Price'
        })
    )
    
    max_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-[#111518] focus:outline-0 focus:ring-0 border border-[#dbe1e6] bg-white focus:border-[#dbe1e6] h-14 placeholder:text-[#617689] p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Max Price'
        })
    )
