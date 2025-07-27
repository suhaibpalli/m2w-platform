from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView, PasswordResetConfirmView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView, UpdateView
from .forms import CompanyRegistrationForm, CustomLoginForm, CompanyProfileForm
from .models import Company

class RegisterView(CreateView):
    form_class = CompanyRegistrationForm
    template_name = 'accounts/register.html'
    success_url = '/payments/checkout/'  # Will redirect to payment after registration

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        role = user.company.role
        if role == 'vendor':
            messages.success(
                self.request,
                'Registration successful! Please complete your payment to activate your vendor account.'
            )
            return redirect('/payments/checkout/')
        else:
            messages.success(
                self.request,
                'Registration successful! Welcome aboard. You can now browse the marketplace.'
            )
            return redirect('dashboard:home')  # ← Changed this line
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class CustomLoginView(LoginView):
    form_class = CustomLoginForm
    template_name = 'accounts/login.html'
    
    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me')
        if remember_me:
            self.request.session.set_expiry(1209600)  # 2 weeks
        else:
            self.request.session.set_expiry(0)  # Browser close
        
        messages.success(self.request, 'Welcome back!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hide_header'] = True  # Hide main navigation on login page
        return context

class CustomLogoutView(LogoutView):
    next_page = '/'
    http_method_names = ['get', 'post']

    def get(self, request, *args, **kwargs):
        from django.contrib.auth import logout
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect(self.next_page)

    def post(self, request, *args, **kwargs):
        from django.contrib.auth import logout
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect(self.next_page)

class CustomPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    success_url = reverse_lazy('accounts:password_reset_done')
    
    def form_valid(self, form):
        messages.success(self.request, 'Password reset email has been sent to your email address.')
        return super().form_valid(form)

class PasswordResetDoneView(TemplateView):
    template_name = 'accounts/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')

class PasswordResetCompleteView(TemplateView):
    template_name = 'accounts/password_reset_complete.html'

class ProfileView(LoginRequiredMixin, UpdateView):
    model = Company
    form_class = CompanyProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')
    
    def get_object(self):
        return self.request.user.company
    
    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        context['company'] = self.request.user.company
        return context

@login_required
def profile_redirect(request):
    """Redirect to profile based on user type"""
    return redirect('accounts:profile')
