from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Company
from core.models import Industry

class CompanyRegistrationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=Company.ROLE_CHOICES,
        widget=forms.RadioSelect,
        initial='vendor',
        label="Account Type"
    )
    company_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#121416] focus:outline-0 focus:ring-0 border border-[#dde1e3] bg-white focus:border-[#dde1e3] h-14 placeholder:text-[#6a7681] p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Enter your company name'
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#121416] focus:outline-0 focus:ring-0 border border-[#dde1e3] bg-white focus:border-[#dde1e3] h-14 placeholder:text-[#6a7681] p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Enter your email'
        })
    )
    
    industries = forms.ModelMultipleChoiceField(
        queryset=Industry.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'h-5 w-5 rounded border-[#dde1e3] border-2 bg-transparent text-[#dce8f3] checked:bg-[#dce8f3] checked:border-[#dce8f3] focus:ring-0 focus:ring-offset-0 focus:border-[#dde1e3] focus:outline-none'
        }),
        required=False
    )
    
    other_industry = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#121416] focus:outline-0 focus:ring-0 border border-[#dde1e3] bg-white focus:border-[#dde1e3] h-14 placeholder:text-[#6a7681] p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Specify other industry'
        })
    )
    
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-5 w-5 rounded border-[#dde1e3] border-2 bg-transparent text-[#dce8f3] checked:bg-[#dce8f3] checked:border-[#dce8f3] focus:ring-0 focus:ring-offset-0 focus:border-[#dde1e3] focus:outline-none'
        })
    )

    class Meta:
        model = User
        fields = (
            'role', 'email', 'company_name',
            'password1', 'password2',
            'industries', 'other_industry', 'terms_accepted'
        )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove username field and use email as username
        self.fields.pop('username', None)
        
        # Customize password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#121416] focus:outline-0 focus:ring-0 border border-[#dde1e3] bg-white focus:border-[#dde1e3] h-14 placeholder:text-[#6a7681] p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Create a password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#121416] focus:outline-0 focus:ring-0 border border-[#dde1e3] bg-white focus:border-[#dde1e3] h-14 placeholder:text-[#6a7681] p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Confirm password'
        })
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            # Update company details
            company = user.company
            # set role
            company.role = self.cleaned_data['role']
            company.company_name = self.cleaned_data['company_name']
            company.other_industry = self.cleaned_data.get('other_industry', '')
            
            # Set industries
            if self.cleaned_data['industries']:
                company.industries.set(self.cleaned_data['industries'])

            # For buyers, skip subscription
            if company.role != 'vendor':
                from django.utils import timezone
                company.subscription_status = 'active'
                company.subscription_start_date = timezone.now()
                company.subscription_end_date = None

            company.save()
        
        return user

class CustomLoginForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#121416] focus:outline-0 focus:ring-0 border border-[#dde1e3] bg-white focus:border-[#dde1e3] h-14 placeholder:text-[#6a7681] p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Email'
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#121416] focus:outline-0 focus:ring-0 border border-[#dde1e3] bg-white focus:border-[#dde1e3] h-14 placeholder:text-[#6a7681] p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Password'
        })
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-5 w-5 rounded border-[#dde1e3] border-2 bg-transparent text-[#dce8f3] checked:bg-[#dce8f3] checked:border-[#dce8f3] focus:ring-0 focus:ring-offset-0 focus:border-[#dde1e3] focus:outline-none'
        })
    )

class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            'company_name', 'description', 'contact_email', 'contact_phone',
            'registration_number', 'country_of_registration', 'industries', 'other_industry'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#111518] focus:outline-0 focus:ring-0 border border-[#dbe1e6] bg-white focus:border-[#dbe1e6] h-14 placeholder:text-[#60768a] p-[15px] text-base font-normal leading-normal'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#111518] focus:outline-0 focus:ring-0 border border-[#dbe1e6] bg-white focus:border-[#dbe1e6] min-h-36 placeholder:text-[#60768a] p-[15px] text-base font-normal leading-normal',
                'rows': 4
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#111518] focus:outline-0 focus:ring-0 border border-[#dbe1e6] bg-white focus:border-[#dbe1e6] h-14 placeholder:text-[#60768a] p-[15px] text-base font-normal leading-normal'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#111518] focus:outline-0 focus:ring-0 border border-[#dbe1e6] bg-white focus:border-[#dbe1e6] h-14 placeholder:text-[#60768a] p-[15px] text-base font-normal leading-normal'
            }),
            'registration_number': forms.TextInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#111518] focus:outline-0 focus:ring-0 border border-[#dbe1e6] bg-white focus:border-[#dbe1e6] h-14 placeholder:text-[#60768a] p-[15px] text-base font-normal leading-normal'
            }),
            'country_of_registration': forms.TextInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#111518] focus:outline-0 focus:ring-0 border border-[#dbe1e6] bg-white focus:border-[#dbe1e6] h-14 placeholder:text-[#60768a] p-[15px] text-base font-normal leading-normal'
            }),
            'industries': forms.CheckboxSelectMultiple(),
            'other_industry': forms.TextInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#111518] focus:outline-0 focus:ring-0 border border-[#dbe1e6] bg-white focus:border-[#dbe1e6] h-14 placeholder:text-[#60768a] p-[15px] text-base font-normal leading-normal'
            }),
        }
