from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import json
from .models import Problem, Category


def index(request):
    """Главная страница с картой"""
    # Получаем параметры фильтрации из GET запроса
    selected_categories = request.GET.getlist('category')

    # Получаем выбранный населенный пункт
    selected_location = request.GET.get('location', 'mokshan')

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
        'penza': [53.2001, 45.0046],  # Пенза
        'ramzai': [53.3365, 44.7333],  # Рамзай
    }

    # Выбираем центр карты
    center = locations.get(selected_location, locations['mokshan'])

    # Получаем все категории для фильтра
    categories = Category.objects.all()

    # Создаем JSON с проблемами для передачи в JavaScript
    problems_data = []
    for problem in problems:
        problem_data = {
            'id': problem.id,
            'lat': problem.latitude,
            'lng': problem.longitude,
            'color': problem.get_color(),
            'category': problem.get_category_display(),
            'description': problem.description[:100] + '...' if len(problem.description) > 100 else problem.description,
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

    print(f"DEBUG: API Key = {settings.YANDEX_MAPS_API_KEY}")  # Временная отладка
    print(f"DEBUG: Center = {center}")

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

            print(f"POST данные: lat={latitude}, lng={longitude}, address={address}, category={category_id}")

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
            messages.success(request, 'Проблема успешно добавлена!')
            return redirect('helpcard:problem_detail', problem_id=problem.id)

        except Exception as e:
            messages.error(request, f'Ошибка при добавлении проблемы: {e}')
            print(f"Ошибка: {e}")
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
        messages.error(request, 'Только исполнители могут брать задачи в работу')
        return redirect('helpcard:index')

    problem = get_object_or_404(Problem, id=problem_id)

    if problem.status != 'new':
        messages.error(request, 'Эта задача уже взята в работу или решена')
        return redirect('helpcard:index')

    if request.method == 'POST':
        promised_days = int(request.POST.get('promised_days', 3))

        problem.status = 'in_progress'
        problem.assigned_to = request.user
        problem.assigned_at = timezone.now()
        problem.promised_deadline = timezone.now() + timedelta(days=promised_days)
        problem.save()

        messages.success(request, f'Задача взята в работу! Срок: {promised_days} дней')
        return redirect('helpcard:index')

    # GET запрос - показываем форму
    return render(request, 'helpcard/take_problem.html', {'problem': problem})


@login_required
def complete_problem(request, problem_id):
    """Отметить проблему как решенную"""
    problem = get_object_or_404(Problem, id=problem_id)

    # Проверяем права
    if request.user.role != 'admin' and problem.assigned_to != request.user:
        messages.error(request, 'У вас нет прав отметить эту задачу как решенную')
        return redirect('helpcard:index')

    problem.status = 'solved'
    problem.save()

    messages.success(request, 'Задача отмечена как решенная!')
    return redirect('helpcard:index')
