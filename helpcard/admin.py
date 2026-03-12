from django.contrib import admin
from .models import Category, Problem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name')


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_category_display', 'status', 'created_at', 'assigned_to')
    list_filter = ('status', 'category')
    search_fields = ('description',)
