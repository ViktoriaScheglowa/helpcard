# users/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import User
from helpcard.models import Category


def register(request):
    """Регистрация нового пользователя"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        role = request.POST.get('role', 'user')

        # Проверка паролей
        if password != password2:
            messages.error(request, 'Пароли не совпадают')
            return redirect('users:register')

        # Проверка существования пользователя
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Пользователь с таким именем уже существует')
            return redirect('users:register')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Пользователь с таким email уже существует')
            return redirect('users:register')

        # Создание пользователя
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role
        )

        messages.success(request, 'Регистрация успешна! Теперь вы можете войти.')
        return redirect('login')

    return render(request, 'users/register.html')


@login_required
def profile(request):
    """Профиль пользователя с подписками"""
    if request.method == 'POST':
        # Обновляем подписки на категории
        category_ids = request.POST.getlist('categories')
        request.user.subscribed_categories = [int(id) for id in category_ids]
        request.user.save()

        messages.success(request, 'Настройки сохранены!')
        return redirect('users:profile')

    # Получаем все категории для отображения
    categories = Category.objects.all()

    context = {
        'categories': categories,
        'subscribed': request.user.subscribed_categories,
    }

    return render(request, 'users/profile.html', context)
