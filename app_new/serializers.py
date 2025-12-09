# backend/app_new/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Income, Expense_tbl, Category, BudgetCategoryMonth, UserProfile
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class IncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Income
        fields = ['id', 'amount', 'source', 'date']


class ExpenseTblSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(source='cid.id', read_only=True)
    category_name = serializers.CharField(source='cid.name', read_only=True)
    cid = serializers.IntegerField(write_only=True)

    class Meta:
        model = Expense_tbl
        fields = ['id', 'amount', 'cid', 'category_id', 'category_name', 'date', 'note']

    def create(self, validated_data):
        category_id = validated_data.pop('cid')
        user = self.context['request'].user
        category = Category.objects.get(id=category_id)
        expense = Expense_tbl.objects.create(user=user, cid=category, **validated_data)
        return expense

    def update(self, instance, validated_data):
        if 'cid' in validated_data:
            category_id = validated_data.pop('cid')
            instance.cid = Category.objects.get(id=category_id)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# THIS IS THE ONE YOU NEED — DO NOT DELETE
# backend/app_new/serializers.py

class CategoryWithMonthlyBudgetSerializer(serializers.ModelSerializer):
    budget = serializers.SerializerMethodField()
    spent = serializers.SerializerMethodField()
    remaining = serializers.SerializerMethodField()
    transaction_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'description',
            'total_expense', 'budget', 'spent', 'remaining', 'transaction_count'
        ]

    def get_budget(self, obj):
       user = self.context['request'].user
       year = self.context.get('selected_year', timezone.now().year)
       month = self.context.get('selected_month', timezone.now().month)
       try:
          budget_obj = BudgetCategoryMonth.objects.get(
            uid=user, category=obj, year=year, month=month
          )
          return float(budget_obj.amount)
       except BudgetCategoryMonth.DoesNotExist:
         return 0.0

    def get_spent(self, obj):
      user = self.context['request'].user
      year = self.context.get('selected_year', timezone.now().year)
      month = self.context.get('selected_month', timezone.now().month)
      total = Expense_tbl.objects.filter(
        user=user, cid=obj,
        date__year=year, date__month=month
      ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
      return float(total)

    def get_remaining(self, obj):
        return self.get_budget(obj) - self.get_spent(obj)

    def get_transaction_count(self, obj):
        user = self.context['request'].user
        today = timezone.now()
        return Expense_tbl.objects.filter(
            user=user,
            cid=obj,
            date__year=today.year,
            date__month=today.month
        ).count()


class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['name', 'description']

    def validate_name(self, value):
        if Category.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("Category with this name already exists.")
        return value


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['fixed_expenses', 'savings_target_percent']