# backend/app_new/urls.py
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    RegisterView, IncomeView, ExpenseView,get_categories,
    CategoryView, CategoryDetailView, 
    PredefinedCategoriesView, category_summary_view,
    update_category_budget, budget_summary, auto_assign_budgets,reports_view,category_list_with_budget,update_monthly_budget,
    UserProfileView  # ← Now this exists!
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Income
    path('api/income/', IncomeView.as_view(), name='income'),
    path('api/income/<int:pk>/', IncomeView.as_view(), name='income-detail'),
    
    # Expense
    path('api/expense/', ExpenseView.as_view(), name='expense'),
    path('api/expense/<int:pk>/', ExpenseView.as_view(), name='expense-detail'),
    
    # Categories
    path('api/categories/', CategoryView.as_view(), name='category-list-create'),
    path('api/categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    path('api/categories/predefined/', PredefinedCategoriesView.as_view(), name='predefined-categories'),
    path('api/categories/summary/', category_summary_view, name='category-summary'),
    
    # Budget & Profile
    path('api/user-profile/', UserProfileView.as_view(), name='user-profile'),
    path('api/budget-summary/', budget_summary, name='budget-summary'),
    path('api/auto-assign-budgets/', auto_assign_budgets, name='auto-assign'),
    path('api/categories/<int:pk>/update-budget/', update_category_budget, name='update-budget'),

   # ADD THESE NEW ONES
    path('api/categories/', category_list_with_budget),  # ← now works with monthly budget
    path('api/categories-with-budget/', category_list_with_budget),  # ← both URLs work
    path('api/reports/', reports_view),
    path('api/categories/<int:category_id>/update-monthly-budget/', update_monthly_budget),
    path('api/auto-assign-budgets/', auto_assign_budgets),
    path('api/categories/', get_categories),
    path('api/categories-with-budget/', get_categories),  # optional
    
]