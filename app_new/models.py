# # app/models.py
# from django.db import models
# from django.contrib.auth.models import User
# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver
# from django.db import transaction

# # Income model name - app_Income 
# class Income(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     source = models.CharField(max_length=100)
#     date = models.DateField()

#     def __str__(self):
#         return f"{self.user.username} - {self.source} - {self.amount}"
    
# class Category(models.Model):
#     name = models.CharField(max_length=100, unique=True)
#     description = models.TextField(blank=True, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     budget = models.DecimalField(max_digits=5, decimal_places=2, default=0.00) 
#     total_expense = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
#     # total_expense = models.DecimalField(max_digits=12, decimal_places=2, default=0)

#     class Meta:
#         ordering = ['name']
    
#     def __str__(self):
#         return self.name

#     def get_total_expenses(self, user):
#         """Helper method to get total expenses for this category for a specific user"""
#         from django.db.models import Sum
#         return Expense_tbl.objects.filter(user=user, cid=self).aggregate(
#             total=Sum('amount')
#         )['total'] or 0
    
#     def update_total_expense(self, user):
#         """Safely update cached total for this category and user"""
#         from django.db.models import Sum
#         total = Expense_tbl.objects.filter(cid=self, user=user).aggregate(
#             total=Sum('amount')
#         )['total'] or 0
#         self.total_expense = total
#         self.save(update_fields=['total_expense'])

# # Expense model name - app_new_expense_tbl   
# class Expense_tbl(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     cid = models.ForeignKey(Category, on_delete=models.CASCADE)  # Links to Category ID
#     date = models.DateField()
#     note = models.TextField(blank=True, null=True)
    
#     def __str__(self):
#         return f"{self.user.username} - {self.amount} - {self.cid.name}"
    

# @receiver([post_save, post_delete], sender=Expense_tbl)
# def update_category_total_safe(sender, instance, **kwargs):
#     """
#     CORRECTED: Capture instance.id and cid.id to avoid stale references
#     """
#     # Capture IDs instead of objects → 100% safe
#     expense_id = instance.id
#     category_id = instance.cid_id
#     user_id = instance.user_id

#     def _update():
#         try:
#             # Re-fetch fresh objects inside the callback
#             category = Category.objects.get(id=category_id)
#             user = User.objects.get(id=user_id)
#             category.update_total_expense(user=user)
#         except (Category.DoesNotExist, User.DoesNotExist):
#             pass  # Silently ignore if deleted

#     transaction.on_commit(_update)



# class UserProfile(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     fixed_expenses = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # e.g., rent, EMI
#     savings_target_percent = models.IntegerField(default=33)  # 33% = 1/3rd

#     def __str__(self):
#         return f"Profile for {self.user.username}"

# # Auto-create profile when user registers
# @receiver(post_save, sender=User)
# def create_user_profile(sender, instance, created, **kwargs):
#     if created:
#         UserProfile.objects.create(user=instance)




# ----new one----

# app/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from django.db.models import Sum
from decimal import Decimal
import datetime

class Income(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    source = models.CharField(max_length=100)
    date = models.DateField()
    def __str__(self):
        return f"{self.user.username} - {self.source} - {self.amount}"

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_expense = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def update_total_expense(self, user):
        total = Expense_tbl.objects.filter(cid=self, user=user).aggregate(total=Sum('amount'))['total'] or 0
        self.total_expense = total
        self.save(update_fields=['total_expense'])

# NEW MODEL: Monthly Budget per Category per User
class BudgetCategoryMonth(models.Model):
    uid = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    year = models.IntegerField()
    month = models.IntegerField()  # 1-12
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ('uid', 'category', 'year', 'month')
        indexes = [
            models.Index(fields=['uid', 'year', 'month']),
        ]

    def __str__(self):
        return f"{self.uid} - {self.category.name} - {self.year}-{self.month}: ₹{self.amount}"

class Expense_tbl(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    cid = models.ForeignKey(Category, on_delete=models.CASCADE)
    date = models.DateField()
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.cid.name}"

@receiver([post_save, post_delete], sender=Expense_tbl)
def update_category_total_safe(sender, instance, **kwargs):
    expense_id = instance.id
    category_id = instance.cid_id
    user_id = instance.user_id

    def _update():
        try:
            category = Category.objects.get(id=category_id)
            user = User.objects.get(id=user_id)
            category.update_total_expense(user=user)
        except (Category.DoesNotExist, User.DoesNotExist):
            pass
    transaction.on_commit(_update)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    fixed_expenses = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    savings_target_percent = models.IntegerField(default=33)

    def __str__(self):
        return f"Profile for {self.user.username}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)