# backend/app/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q, DecimalField
from django.db.models.functions import Coalesce
from django.db import models
from django.db.models.functions import TruncMonth, TruncYear
from collections import defaultdict
from django.utils import timezone
from dateutil.relativedelta import relativedelta
import calendar
from .models import Income, Expense_tbl, Category, BudgetCategoryMonth, UserProfile  # ← THIS LINE IS CRITICAL
from django.contrib.auth import authenticate, login
from .serializers import (
    RegisterSerializer, 
    IncomeSerializer, 
    ExpenseTblSerializer, CategoryCreateSerializer, CategoryWithMonthlyBudgetSerializer
)
from .models import Income, Expense_tbl, Category
from .models import UserProfile
from .serializers import UserProfileSerializer
from rest_framework.permissions import AllowAny
from datetime import datetime

# Register API
class RegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class IncomeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        incomes = Income.objects.filter(user=request.user)
        serializer = IncomeSerializer(incomes, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = IncomeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        try:
            income = Income.objects.get(pk=pk, user=request.user)
        except Income.DoesNotExist:
            return Response({"error": "Income not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = IncomeSerializer(income, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            income = Income.objects.get(pk=pk, user=request.user)
        except Income.DoesNotExist:
            return Response({"error": "Income not found"}, status=status.HTTP_404_NOT_FOUND)

        income.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# FIXED: ExpenseView with proper create() method
class ExpenseView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        """
        GET /api/expense/      → List all expenses
        GET /api/expense/1/    → Get single expense
        """
        if pk is None:
            print(f"📥 GET /api/expense/ - User: {request.user.id}")
            expenses = Expense_tbl.objects.filter(
                user=request.user
            ).select_related('cid').order_by('-date')
            
            serializer = ExpenseTblSerializer(expenses, many=True, context={'request': request})
            print(f"✅ Found {len(serializer.data)} expenses")
            return Response(serializer.data)
        
        else:
            try:
                expense = Expense_tbl.objects.get(pk=pk, user=request.user)
                serializer = ExpenseTblSerializer(expense, context={'request': request})
                return Response(serializer.data)
            except Expense_tbl.DoesNotExist:
                return Response(
                    {"error": "Expense not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )

    def post(self, request):
        """POST /api/expense/ → Create new expense"""
        print(f"📥 POST /api/expense/ - Data: {request.data}")
        
        # FIXED: Use context for serializer
        serializer = ExpenseTblSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            print("✅ Validation passed")
            # CRITICAL FIX: serializer.save() now returns instance
            expense = serializer.save()
            response_serializer = ExpenseTblSerializer(
                expense, 
                context={'request': request}
            )
            print("✅ Expense created successfully")
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        else:
            print("❌ Validation errors:", serializer.errors)
            return Response({
                "error": "Failed to create expense",
                "details": serializer.errors,
                "input_data": request.data
            }, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """PUT /api/expense/1/ → Update expense"""
        try:
            expense = Expense_tbl.objects.get(pk=pk, user=request.user)
        except Expense_tbl.DoesNotExist:
            return Response(
                {"error": "Expense not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ExpenseTblSerializer(
            expense, 
            data=request.data, 
            partial=True, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """DELETE /api/expense/1/ → Delete expense"""
        try:
            expense = Expense_tbl.objects.get(pk=pk, user=request.user)
            expense.delete()
            return Response(
                {"message": "Expense deleted successfully"}, 
                status=status.HTTP_200_OK
            )
        except Expense_tbl.DoesNotExist:
            return Response(
                {"error": "Expense not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

# INTEGRATED: CategoryView with function-based improvements
class CategoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        """GET /api/categories/ - List all categories with expense summary"""
        if pk is None:
            # FIXED: Include expense summary for current user only
            categories = Category.objects.all()
            
            # Add search functionality
            search = request.query_params.get('search', None)
            if search:
                categories = categories.filter(
                    Q(name__icontains=search) | 
                    Q(description__icontains=search)
                )
            
            # Sort by name
            categories = categories.order_by('name')
            
            serializer = CategoryWithMonthlyBudgetSerializer(
                   categories, many=True, context={'request': request}
            )
            
            # FIXED: Proper DecimalField aggregation
            user_expenses = Expense_tbl.objects.filter(user=request.user).aggregate(
                total=Coalesce(
                    Sum('amount'), 
                    0, 
                    output_field=DecimalField(max_digits=12, decimal_places=2)  # ✅ CRITICAL FIX
                )
            )['total'] or 0
            
            # Enhanced response with totals
            return Response({
                'categories': serializer.data,
                'total_categories': categories.count(),
                'total_expenses': float(user_expenses),  # ✅ Safe conversion
                'active_categories': len([cat for cat in serializer.data if cat['transaction_count'] > 0])
            })
        
        else:
            try:
                category = Category.objects.get(pk=pk)
                serializer = CategorySerializer(category, context={'request': request})
                return Response(serializer.data)
            except Category.DoesNotExist:
                return Response(
                    {"error": "Category not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )

    def post(self, request):
        """POST /api/categories/ - Create new category"""
        serializer = CategoryCreateSerializer(data=request.data)
        if serializer.is_valid():
            category = serializer.save()
            detail_serializer = CategoryCreateSerializer(
                category, 
                context={'request': request}
            )
            return Response(
                detail_serializer.data, 
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class CategoryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        """PUT /api/categories/1/ - Update category"""
        try:
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response(
                {"error": "Category not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = CategoryCreateSerializer(
            category, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            detail_serializer = CategorySerializer(
                serializer.instance, 
                context={'request': request}
            )
            return Response(detail_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """DELETE /api/categories/1/ - Delete category"""
        try:
            category = Category.objects.get(pk=pk)
            
            # Check if category has expenses for current user
            expense_count = Expense_tbl.objects.filter(cid=category, user=request.user).count()
            if expense_count > 0:
                return Response({
                    "error": f"Cannot delete category with {expense_count} existing expenses."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            category.delete()
            return Response(
                {"message": "Category deleted successfully"}, 
                status=status.HTTP_200_OK
            )
        except Category.DoesNotExist:
            return Response(
                {"error": "Category not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

# Predefined categories endpoint
class PredefinedCategoriesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        predefined = [
            {"name": "Food & Dining", "description": "Meals, restaurants, groceries"},
            {"name": "Transportation", "description": "Fuel, public transport, taxi"},
            {"name": "Shopping", "description": "Clothes, electronics, household items"},
            {"name": "Bills & Utilities", "description": "Electricity, water, internet"},
            {"name": "Entertainment", "description": "Movies, concerts, subscriptions"},
            {"name": "Health", "description": "Medical, gym, medicines"},
            {"name": "Education", "description": "Books, courses, tuition"},
            {"name": "Travel", "description": "Flights, hotels, vacation"},
            {"name": "Other", "description": "Miscellaneous expenses"},
        ]
        
        # Filter out categories that already exist
        existing_names = set(
            Category.objects.values_list('name', flat=True)
        )
        available = [cat for cat in predefined if cat['name'] not in existing_names]
        
        return Response({
            'predefined_categories': available,
            'total_available': len(available)
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def category_summary_view(request):
    """
    GET /api/categories/summary/ - Get categories with expense summary
    """
    categories = Category.objects.all()
    user = request.user
    
    summary_data = []
    total_expenses = 0
    
    for category in categories:
        expenses = Expense_tbl.objects.filter(user=user, cid=category)
        total_amount = expenses.aggregate(total=Coalesce(Sum('amount'), 0))['total'] or 0
        transaction_count = expenses.count()
        
        if total_amount > 0:
            percentage = round((float(total_amount) / float(total_expenses + total_amount)) * 100, 1)
        else:
            percentage = 0
            
        summary_data.append({
            'category': category.id,
            'category_name': category.name,
            'total_amount': float(total_amount),
            'transaction_count': transaction_count,
            'percentage': percentage
        })
        total_expenses += total_amount
    
    # Update percentages
    for item in summary_data:
        if total_expenses > 0:
            item['percentage'] = round((item['total_amount'] / total_expenses) * 100, 1)
    
    return Response({
        'categories': summary_data,
        'total_expenses': float(total_expenses)
    })

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_category_budget(request, pk):
    try:
        category = Category.objects.get(pk=pk)
    except Category.DoesNotExist:
        return Response({"error": "Category not found"}, status=404)

    budget = request.data.get("budget")

    if budget is None:
        return Response({"error": "Budget field is required"}, status=400)

    try:
        budget_value = Decimal(str(budget))
        if budget_value < 0:
            return Response({"error": "Budget cannot be negative"}, status=400)
    except (ValueError, decimal.InvalidOperation, TypeError):
        return Response({"error": "Invalid budget value"}, status=400)

    category.budget = budget_value
    category.save()

    return Response({"budget": float(budget_value)})

def get_year_month(request):
    year = int(request.query_params.get('year', timezone.now().year))
    month = int(request.query_params.get('month', timezone.now().month))
    if month < 1 or month > 12:
        month = timezone.now().month
    return year, month



from decimal import Decimal
import decimal
# views.py - REPLACE THESE FUNCTIONS

from django.utils import timezone
from datetime import datetime

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def budget_summary(request):
    user = request.user
    year, month = get_year_month(request)

    total_income = Income.objects.filter(
        user=user, date__year=year, date__month=month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    profile, _ = UserProfile.objects.get_or_create(user=user)
    fixed = Decimal(profile.fixed_expenses or 0)
    savings_percent = Decimal(profile.savings_target_percent or 33) / 100
    savings = total_income * savings_percent
    spendable = total_income - fixed - savings

    month_name = calendar.month_name[month]

    return Response({
        "year": year,
        "month": month,
        "month_name": month_name,
        "total_income_this_month": float(total_income),
        "fixed_expenses": float(fixed),
        "savings_target_percent": int(profile.savings_target_percent),
        "savings_amount": float(savings),
        "spendable": max(float(spendable), 0),
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def category_list_with_budget(request):
    user = request.user
    year, month = get_year_month(request)

    categories = Category.objects.all().order_by('name')
    serializer = CategoryWithMonthlyBudgetSerializer(
        categories, many=True, context={'request': request, 'selected_year': year, 'selected_month': month}
    )
    return Response({
        'categories': serializer.data,
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month]
    })
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_categories(request):
    categories = Category.objects.all().order_by('name')
    serializer = CategoryWithMonthlyBudgetSerializer(
        categories, many=True, context={'request': request}
    )
    return Response({'categories': serializer.data})


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_monthly_budget(request, category_id):
    user = request.user
    year = int(request.data.get('year', timezone.now().year))
    month = int(request.data.get('month', timezone.now().month))
    budget = Decimal(str(request.data.get("budget", 0)))

    if budget < 0:
        return Response({"error": "Budget cannot be negative"}, status=400)

    obj, created = BudgetCategoryMonth.objects.update_or_create(
        uid=user,
        category_id=category_id,
        year=year,
        month=month,
        defaults={"amount": budget}
    )

    return Response({"budget": float(obj.amount), "year": year, "month": month})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auto_assign_budgets(request):
    user = request.user
    year = int(request.data.get('year', timezone.now().year))
    month = int(request.data.get('month', timezone.now().month))

    total_income = Income.objects.filter(
        user=user, date__year=year, date__month=month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    if total_income <= 0:
        return Response({"error": f"No income recorded for {calendar.month_name[month]} {year}"}, status=400)

    profile, _ = UserProfile.objects.get_or_create(user=user)
    savings_rate = Decimal(profile.savings_target_percent or 33) / 100
    fixed = Decimal(profile.fixed_expenses or 0)
    spendable = total_income - (total_income * savings_rate) - fixed

    if spendable <= 0:
        return Response({"error": "Not enough spendable income after savings & fixed expenses"}, status=400)

    categories = Category.objects.all()
    split = {
        "Food & Dining": 0.30,
        "Transportation": 0.15,
        "Shopping": 0.10,
        "Bills & Utilities": 0.15,
        "Entertainment": 0.10,
        "Health": 0.10,
        "Education": 0.05,
        "Travel": 0.03,
        "Other": 0.02,
    }

    assigned = Decimal('0')
    updated = []

    for name, pct in split.items():
        try:
            cat = categories.get(name__iexact=name)
            budget = (spendable * Decimal(str(pct))).quantize(Decimal('1'), rounding='ROUND_HALF_UP')
            BudgetCategoryMonth.objects.update_or_create(
                uid=user, category=cat, year=year, month=month,
                defaults={"amount": budget}
            )
            updated.append({"name": cat.name, "budget": float(budget)})
            assigned += budget
        except Category.DoesNotExist:
            continue

    remaining = spendable - assigned
    others = categories.exclude(name__in=[k for k in split.keys()])
    if others.exists() and remaining > 0:
        per_cat = (remaining / len(others)).quantize(Decimal('1'), rounding='ROUND_HALF_UP')
        for cat in others:
            BudgetCategoryMonth.objects.update_or_create(
                uid=user, category=cat, year=year, month=month,
                defaults={"amount": per_cat}
            )
            updated.append({"name": cat.name, "budget": float(per_cat)})

    return Response({
        "message": f"Budgets assigned for {calendar.month_name[month]} {year}!",
        "year": year,
        "month": month,
        "updated_categories": updated,
        "total_income": float(total_income),
        "spendable": float(spendable),
    })

# ──────────────────────────────────────────────────────────────
# USER PROFILE VIEW – WAS MISSING! (This fixes the ImportError)
# ──────────────────────────────────────────────────────────────
class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)

    def post(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# views.py → Replace the old reports_view completely
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reports_view(request):
    user = request.user
    year = int(request.query_params.get('year', timezone.now().year))
    month = int(request.query_params.get('month', timezone.now().month))

    # Income for selected month
    income_total = Income.objects.filter(
        user=user, date__year=year, date__month=month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # Expenses for selected month
    expenses = Expense_tbl.objects.filter(
        user=user, date__year=year, date__month=month
    )
    expense_total = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # Category breakdown
    category_data = expenses.values('cid__id', 'cid__name').annotate(
        spent=Sum('amount')
    )

    # Get budgets for this month
    budgets = BudgetCategoryMonth.objects.filter(
        uid=user, year=year, month=month
    ).values('category_id', 'amount')
    budget_map = {b['category_id']: float(b['amount']) for b in budgets}

    categories_report = []
    for item in category_data:
        cat_id = item['cid__id']
        cat_name = item['cid__name']
        spent = float(item['spent'] or 0)
        budget = budget_map.get(cat_id, 0.0)
        remaining = budget - spent
        status = "Over Budget" if spent > budget and budget > 0 else "Under Budget" if budget > 0 else "No Budget"

        categories_report.append({
            "category": cat_name,
            "spent": spent,
            "budget": budget,
            "remaining": remaining,
            "status": status
        })

    savings = income_total - expense_total
    savings_rate = (savings / income_total * 100) if income_total > 0 else 0

    return Response({
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "income": float(income_total),
        "expenses": float(expense_total),
        "savings": float(savings),
        "savings_rate": round(savings_rate, 1),
        "status": "Excellent" if savings_rate >= 30 else "Good" if savings_rate >= 20 else "Fair" if savings_rate >= 10 else "Critical",
        "categories": categories_report
    })