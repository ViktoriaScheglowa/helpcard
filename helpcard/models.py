from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import json

User = get_user_model()


class Category(models.Model):
    """Категории проблем"""
    name = models.CharField(max_length=50, unique=True, verbose_name='Название')
    display_name = models.CharField(max_length=100, verbose_name='Отображаемое имя')
    icon = models.CharField(max_length=50, blank=True, verbose_name='Иконка')

    def __str__(self):
        return self.display_name

    def is_selected(self, selected_categories):
        """Проверяет, выбрана ли категория в фильтре"""
        return self.name in selected_categories

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'


class Problem(models.Model):
    """Модель проблемы"""
    STATUS_CHOICES = [
        ('new', 'Новая'),
        ('in_progress', 'В работе'),
        ('solved', 'Решена'),
        ('overdue', 'Просрочена'),
    ]

    # Координаты
    latitude = models.FloatField(verbose_name='Широта')
    longitude = models.FloatField(verbose_name='Долгота')

    # Адрес (можно получить по координатам)
    address = models.CharField(max_length=300, blank=True, verbose_name='Адрес')

    # Описание
    description = models.TextField(verbose_name='Описание проблемы')

    # Категория
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Категория'
    )

    # Даты
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлена')

    # Статус
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name='Статус'
    )

    # Связи с пользователями
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_problems',
        verbose_name='Создана пользователем'
    )

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_problems',
        verbose_name='Назначена исполнителю'
    )

    # Сроки
    assigned_at = models.DateTimeField(null=True, blank=True, verbose_name='Назначена')
    promised_deadline = models.DateTimeField(null=True, blank=True, verbose_name='Обещанный срок')
    location_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Населенный пункт',
        help_text='Например: Мокшан, Пенза, Рамзай'
    )

    # Поле для комментария исполнителя
    executor_comment = models.TextField(
        blank=True,
        verbose_name='Комментарий исполнителя'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Проблема'
        verbose_name_plural = 'Проблемы'

    def __str__(self):
        return f"#{self.id} - {self.get_category_display()} - {self.created_at.strftime('%d.%m.%Y')}"

    def get_category_display(self):
        """Получить отображаемое имя категории"""
        return self.category.display_name if self.category else 'Без категории'

    def get_color(self):
        """Определяет цвет проблемы на основе статуса и времени"""
        now = timezone.now()

        # Если проблема решена
        if self.status == 'solved':
            return 'gray'

        # Если проблема в работе
        if self.status == 'in_progress':
            if self.promised_deadline and now > self.promised_deadline:
                return 'darkred'  # Просрочил обещание
            return 'blue'

        # Если проблема просрочена
        if self.status == 'overdue':
            return 'red'

        # Новая проблема - считаем дни
        days_passed = (now - self.created_at).days

        if days_passed >= 7:
            return 'red'
        elif days_passed >= 3:
            return 'orange'
        else:
            return 'green'

    def update_status_by_time(self):
        """Автоматически обновляет статус в зависимости от времени"""
        now = timezone.now()
        days_passed = (now - self.created_at).days

        if self.status == 'new':
            if days_passed >= 7:
                self.status = 'overdue'
                self.save()

        elif self.status == 'in_progress':
            if self.promised_deadline and now > self.promised_deadline:
                self.status = 'overdue'
                self.save()
