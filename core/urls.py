from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.views.generic import RedirectView
from .views import *

router = DefaultRouter()
router.register(r'transactions', TransactionViewSet, basename='transactions')
router.register(r'budgets', BudgetViewSet, basename='budgets')
router.register(r'goals', GoalViewSet, basename='goals')

urlpatterns = [
    path('', RedirectView.as_view(url='/login/', permanent=False)),  # 👈 Redirect root to /login/

    path('', include(router.urls)),

    # API Endpoints
    path('logout/', logout_view, name='logout'),

    # Auth & Core UI Views
    path('register/', register, name='register'),
    path('login/', login_view, name='login'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('transactions-page/', transactions_page, name='transactions_page'),
    path('budgets-page/', budgets_page, name='budgets_page'),
    path('goals-page/', goals_page, name='goals_page'),

    # HTML Views for Feature Pages
    path('upi/', upi_page, name='upi_page'),
    path('generate-upi/', generate_upi_page, name='generate_upi_page'),
]
