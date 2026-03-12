from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta, datetime
import folium
import json
from django.conf import settings
from .models import Problem, Category


def index(request):
    """Главная страница с картой"""
    # Получаем параметры фильтрации из GET запроса
    selected_categories = request.GET.getlist('category')

    # Базовый запрос
    problems = Problem.objects.all()

    # Применяем фильтр по категориям
    if selected_categories:
        problems = problems.filter(category__name__in=selected_categories)

    # Обновляем статусы по времени
    for problem in problems:
        problem.update_status_by_time()

    # Координаты центров населенных пунктов
    locations = {
        'mokshan': [53.4365, 44.6106],  # Мокшан
    }

    # Выбираем центр карты
    center = locations['mokshan']

    # Получаем все категории для фильтра
    categories = Category.objects.all()

    # Добавляем счетчик проблем для каждой категории
    for category in categories:
        category.problem_count = Problem.objects.filter(category=category).count()

    # Создаем JSON с проблемами для передачи в JavaScript
    problems_data = []
    for problem in problems:
        # Определяем цвет маркера
        color = problem.get_color()

        # Создаем словарь с данными проблемы
        problem_data = {
            'id': problem.id,
            'lat': problem.latitude,
            'lng': problem.longitude,
            'color': color,
            'category': problem.get_category_display(),
            'full_description': problem.description,
            'status': problem.get_status_display(),
            'created_at': problem.created_at.strftime('%d.%m.%Y'),
            'assigned_to': problem.assigned_to.username if problem.assigned_to else None,
            'promised_deadline': problem.promised_deadline.strftime('%d.%m.%Y') if problem.promised_deadline else None,
        }

        # Добавляем информацию о кнопках для авторизованных
        if request.user.is_authenticated:
            if request.user.role == 'executor' and problem.status == 'new':
                problem_data['can_take'] = True
            elif request.user.role == 'admin' or (problem.assigned_to == request.user):
                if problem.status != 'solved':
                    problem_data['can_complete'] = True

        problems_data.append(problem_data)

    context = {
        'api_key': settings.YANDEX_MAPS_API_KEY,
        'center_lat': center[0],
        'center_lng': center[1],
        'zoom': 14,
        'categories': categories,
        'selected_categories': selected_categories,
        'problems_json': json.dumps(problems_data),
    }

    return render(request, 'helpcard/index.html', context)


@login_required
def add_problem(request):
    """Добавление новой проблемы"""
    if request.method == 'POST':
        try:
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            address = request.POST.get('address', '')
            category_id = request.POST.get('category_id')
            description = request.POST.get('description')

            # Проверяем обязательные поля
            if not category_id:
                messages.error(request, 'Пожалуйста, выберите категорию')
                return redirect('helpcard:index')

            if not description:
                messages.error(request, 'Пожалуйста, опишите проблему')
                return redirect('helpcard:index')

            # Проверяем, указано ли местоположение
            if (not latitude or not longitude) and not address:
                messages.error(request, 'Пожалуйста, укажите местоположение (кликните на карте или введите адрес)')
                return redirect('helpcard:index')

            # Если есть координаты, используем их
            if latitude and longitude:
                try:
                    lat = float(latitude)
                    lng = float(longitude)
                except ValueError:
                    messages.error(request, 'Некорректные координаты')
                    return redirect('helpcard:index')
            else:
                # Если только адрес, устанавливаем координаты по умолчанию (центр Мокшана)
                lat = 53.4365
                lng = 44.6106

            # Создаем проблему
            problem = Problem(
                latitude=lat,
                longitude=lng,
                address=address,
                description=description,
                category_id=category_id,
                created_by=request.user
            )

            problem.save()

            # Красивое уведомление об успехе
            success_message = (
                '<div class="success-notification">'
                '<div class="success-icon">✅</div>'
                '<div class="success-content">'
                '<div class="success-title">Проблема успешно добавлена!</div>'
                '<div class="success-details">'
                f'<span>ID: #{problem.id}</span>'
                f'<span>{problem.get_category_display()}</span>'
                '</div>'
                '</div>'
                '</div>'
            )
            messages.success(request, success_message)
            return redirect('helpcard:problem_detail', problem_id=problem.id)

        except Exception as e:
            error_message = (
                '<div class="success-notification" style="background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%); border-color: #ef9a9a;">'
                '<div class="success-icon">❌</div>'
                '<div class="success-content">'
                '<div class="success-title" style="color: #b71c1c;">Ошибка!</div>'
                '<div class="success-details">'
                f'<span>{str(e)}</span>'
                '</div>'
                '</div>'
                '</div>'
            )
            messages.error(request, error_message)
            return redirect('helpcard:index')

    return redirect('helpcard:index')


@login_required
def problem_detail(request, problem_id):
    """Детальная страница проблемы"""
    problem = get_object_or_404(Problem, id=problem_id)

    context = {
        'problem': problem,
    }

    return render(request, 'helpcard/problem_detail.html', context)


@login_required
def take_problem(request, problem_id):
    """Взять проблему в работу (для исполнителей)"""
    if request.user.role not in ['executor', 'admin']:
        error_message = (
            '<div class="success-notification" style="background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%); border-color: #ef9a9a;">'
            '<div class="success-icon">⚠️</div>'
            '<div class="success-content">'
            '<div class="success-title" style="color: #b71c1c;">Доступ запрещен</div>'
            '<div class="success-details">'
            '<span>Только исполнители могут брать задачи в работу</span>'
            '</div>'
            '</div>'
            '</div>'
        )
        messages.error(request, error_message)
        return redirect('helpcard:index')

    problem = get_object_or_404(Problem, id=problem_id)

    if problem.status != 'new':
        error_message = (
            '<div class="success-notification" style="background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%); border-color: #ef9a9a;">'
            '<div class="success-icon">⚠️</div>'
            '<div class="success-content">'
            '<div class="success-title" style="color: #b71c1c;">Задача недоступна</div>'
            '<div class="success-details">'
            '<span>Эта задача уже взята в работу или решена</span>'
            '</div>'
            '</div>'
            '</div>'
        )
        messages.error(request, error_message)
        return redirect('helpcard:index')

    if request.method == 'POST':
        # Получаем дату из формы
        deadline = request.POST.get('deadline')
        comment = request.POST.get('comment', '')

        # Преобразуем строку в дату
        deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()

        # Обновляем проблему
        problem.status = 'in_progress'
        problem.assigned_to = request.user
        problem.assigned_at = timezone.now()
        problem.promised_deadline = deadline_date
        if comment:
            problem.executor_comment = comment

        problem.save()

        # Рассчитываем количество дней
        days = (deadline_date - timezone.now().date()).days

        # Формируем красивое сообщение об успехе
        success_message = (
            f'<div class="success-notification">'
            f'<div class="success-icon">✅</div>'
            f'<div class="success-content">'
            f'<div class="success-title">Задача взята в работу!</div>'
            f'<div class="success-details">'
            f'<span class="deadline">📅 Срок: {deadline_date.strftime("%d.%m.%Y")}</span>'
            f'<span class="days">⏱️ {days} дн.</span>'
            f'</div>'
            f'</div>'
            f'</div>'
        )

        messages.success(request, success_message)
        return redirect('helpcard:index')

    # GET запрос - показываем форму
    context = {
        'problem': problem,
        'today': timezone.now().date().isoformat(),
        'default_date': (timezone.now().date() + timedelta(days=3)).isoformat(),
    }
    return render(request, 'helpcard/take_problem.html', context)


@login_required
def complete_problem(request, problem_id):
    """Отметить проблему как решенную"""
    problem = get_object_or_404(Problem, id=problem_id)

    # Проверяем права
    if request.user.role != 'admin' and problem.assigned_to != request.user:
        error_message = (
            '<div class="success-notification" style="background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%); border-color: #ef9a9a;">'
            '<div class="success-icon">⚠️</div>'
            '<div class="success-content">'
            '<div class="success-title" style="color: #b71c1c;">Доступ запрещен</div>'
            '<div class="success-details">'
            '<span>У вас нет прав отметить эту задачу как решенную</span>'
            '</div>'
            '</div>'
            '</div>'
        )
        messages.error(request, error_message)
        return redirect('helpcard:index')

    if request.method == 'POST':
        problem.status = 'solved'
        problem.save()

        # Красивое уведомление об успехе
        success_message = (
            '<div class="success-notification">'
            '<div class="success-icon">🎉</div>'
            '<div class="success-content">'
            '<div class="success-title">Задача отмечена как решенная!</div>'
            '<div class="success-details">'
            '<span>Спасибо за вашу работу!</span>'
            '</div>'
            '</div>'
            '</div>'
        )
        messages.success(request, success_message)
        return redirect('helpcard:index')

    # GET запрос - показываем страницу подтверждения
    context = {
        'problem': problem,
    }
    return render(request, 'helpcard/complete_problem.html', context)
