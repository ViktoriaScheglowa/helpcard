from django.urls import path
from . import views

app_name = 'helpcard'

urlpatterns = [
    path('', views.index, name='index'),
    path('add_problem/', views.add_problem, name='add_problem'),
    path('problem/<int:problem_id>/', views.problem_detail, name='problem_detail'),
    path('take_problem/<int:problem_id>/', views.take_problem, name='take_problem'),
    path('complete_problem/<int:problem_id>/', views.complete_problem, name='complete_problem'),
]
