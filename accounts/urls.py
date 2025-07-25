from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    
    # Password Reset
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset-complete/', views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    # Profile
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('', views.profile_redirect, name='profile_redirect'),
]
