from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Расширенная модель пользователя"""
    ROLE_CHOICES = [
        ('user', 'Житель'),
        ('executor', 'Исполнитель'),
        ('admin', 'Администратор'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='user',
        verbose_name='Роль'
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')

    # Подписки на категории (храним в JSON поле)
    subscribed_categories = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
