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
        phone = request.POST.get('phone', '')  # Добавляем телефон
        password = request.POST.get('password1')  # Изменено с password на password1
        password2 = request.POST.get('password2')
        role = request.POST.get('role', 'user')

        # Валидация
        errors = []

        # Проверка обязательных полей
        if not username:
            errors.append('Имя пользователя обязательно')
        if not email:
            errors.append('Email обязателен')
        if not password:
            errors.append('Пароль обязателен')
        if not password2:
            errors.append('Подтверждение пароля обязательно')

        # Проверка паролей
        if password != password2:
            errors.append('Пароли не совпадают')

        # Проверка длины пароля
        if password and len(password) < 8:
            errors.append('Пароль должен содержать минимум 8 символов')

        # Проверка сложности пароля (опционально)
        if password:
            if not any(char.isdigit() for char in password):
                errors.append('Пароль должен содержать хотя бы одну цифру')
            if not any(char.isupper() for char in password):
                errors.append('Пароль должен содержать хотя бы одну заглавную букву')
            if not any(char.islower() for char in password):
                errors.append('Пароль должен содержать хотя бы одну строчную букву')

        # Проверка существования пользователя
        if username and User.objects.filter(username=username).exists():
            errors.append('Пользователь с таким именем уже существует')

        if email and User.objects.filter(email=email).exists():
            errors.append('Пользователь с таким email уже существует')

        # Если есть ошибки, показываем их и возвращаемся
        if errors:
            for error in errors:
                messages.error(request, error)
            # Возвращаем введенные данные обратно в форму
            return render(request, 'users/register.html', {
                'form_data': {
                    'username': username,
                    'email': email,
                    'phone': phone,
                    'role': role,
                }
            })

        # Создание пользователя
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=role
            )

            # Добавляем телефон, если он был указан
            if phone:
                user.phone = phone
                user.save()

            messages.success(request, 'Регистрация успешна! Теперь вы можете войти.')
            return redirect('login')

        except Exception as e:
            messages.error(request, f'Ошибка при создании пользователя: {str(e)}')
            return redirect('users:register')

    # GET запрос - показываем пустую форму
    return render(request, 'users/register.html', {'form_data': {}})


@login_required
def profile(request):
    """Профиль пользователя с подписками"""
    if request.method == 'POST':
        # Обновляем подписки на категории
        category_ids = request.POST.getlist('categories')
        request.user.subscribed_categories = [int(id) for id in category_ids]

        # Обновляем телефон, если он был передан
        phone = request.POST.get('phone')
        if phone is not None:
            request.user.phone = phone

        request.user.save()

        messages.success(request, 'Настройки сохранены!')
        return redirect('users:profile')

    # Получаем все категории для отображения
    categories = Category.objects.all()

    context = {
        'categories': categories,
        'subscribed': request.user.subscribed_categories,
        'user': request.user,
    }

    return render(request, 'users/profile.html', context)