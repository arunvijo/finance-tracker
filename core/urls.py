from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'transactions', TransactionViewSet, basename='transactions')
router.register(r'budgets', BudgetViewSet, basename='budgets')
router.register(r'goals', GoalViewSet, basename='goals')

urlpatterns = [
    path('', include(router.urls)),

    # API Endpoints
    path('generate-upi-link/', generate_upi, name='generate_upi'),
    path('sms-parser/', sms_parser, name='sms_parser'),
    path('register-api/', register_user_api, name='register_api'),
    path('login-api/', CustomLoginView.as_view(), name='login_api'),
    path('logout/', logout_view, name='logout'),
    path('api/logout/', logout_user, name='logout_user'),
    path('suggest-budget/', suggest_budget, name='suggest_budget'),

    # Extra Feature APIs
    path('voice-entry/', voice_transaction, name='voice_transaction'),
    path('scan-bill/', scan_bill, name='scan_bill'),
    path('health-score/', financial_health_score, name='financial_health_score'),
    path('private-mode/', private_mode_toggle, name='private_mode_toggle'),

    # Auth & Core UI Views
    path('register/', register, name='register'),
    path('login/', login_view, name='login'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('transactions-page/', transactions_page, name='transactions_page'),
    path('budgets-page/', budgets_page, name='budgets_page'),
    path('goals-page/', goals_page, name='goals_page'),

    # HTML Views for Feature Pages
    path('upi/', upi_page, name='upi_page'),
    path('sms/', sms_page, name='sms_page'),
    path('health/', health_score_page, name='health_score_page'),     # ✅ Add this
    path('private/', private_mode_page, name='private_mode_page'),    # ✅ Add this
    path('voice/', voice_transaction_page, name='voice_page'),        # ✅ Add this
    path('scan/', scan_bill_page, name='scan_page'),                  # ✅ Add this
]
