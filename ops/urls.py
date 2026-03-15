# ops/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('',          views.login_view,   name='ops_login'),
    path('logout/',   views.logout_view,  name='ops_logout'),
    path('tasks/',    views.tasklist,     name='ops_tasklist'),
    path('tasks/<int:task_id>/', views.task_detail, name='ops_task_detail'),
    path('tasks/<int:task_id>/confirm/', views.task_confirm, name='ops_task_confirm'),
    path('log/',      views.log_view,     name='ops_log'),
    path('settings/', views.settings_view,name='ops_settings'),
]
