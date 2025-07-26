from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Public product views
    path('', views.ProductListView.as_view(), name='list'),
    path('<int:pk>/', views.ProductDetailView.as_view(), name='detail'),
    path('category/<int:category_id>/', views.CategoryProductsView.as_view(), name='category'),
    
    # Dashboard/Management views
    path('my/', views.MyProductsView.as_view(), name='my_products'),
    path('add/', views.ProductCreateView.as_view(), name='add'),
    path('<int:pk>/edit/', views.ProductUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.ProductDeleteView.as_view(), name='delete'),
]
