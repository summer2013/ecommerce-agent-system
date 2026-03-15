# ops/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone

from tasks.models import AgentTask
from products.models import Product
from stores.models import Store
from logs.models import OperationLog


# ── 登录 / 登出 ──

def login_view(request):
    if request.user.is_authenticated:
        return redirect('ops_tasklist')
    error = None
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password'),
        )
        if user:
            login(request, user)
            return redirect('ops_tasklist')
        error = '用户名或密码错误'
    return render(request, 'ops/login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('ops_login')


# ── 任务列表 ──

@login_required(login_url='/ops/')
def tasklist(request):
    status_filter = request.GET.get('status', 'all')

    qs = AgentTask.objects.all().order_by('-created_at')
    if status_filter != 'all':
        qs = qs.filter(status=status_filter)

    # 统计卡片数据
    stats = {
        'all':       AgentTask.objects.count(),
        'pending':   AgentTask.objects.filter(status='pending').count(),
        'confirmed': AgentTask.objects.filter(status='confirmed').count(),
        'running':   AgentTask.objects.filter(status='running').count(),
        'done':      AgentTask.objects.filter(status='done').count(),
        'failed':    AgentTask.objects.filter(status='failed').count(),
    }

    return render(request, 'ops/tasklist.html', {
        'tasks':         qs,
        'stats':         stats,
        'status_filter': status_filter,
    })


# ── 任务详情 ──

@login_required(login_url='/ops/')
def task_detail(request, task_id):
    task = get_object_or_404(AgentTask, id=task_id)

    # 关联商品或门店
    products = []
    stores   = []
    if task.task_type == AgentTask.TaskType.PRODUCT_PUBLISH:
        product_ids = task.payload.get('product_ids', [])
        products = Product.objects.filter(id__in=product_ids)
    elif task.task_type == AgentTask.TaskType.STORE_DEACTIVATE:
        store_codes = task.payload.get('store_codes', [])
        stores = Store.objects.filter(store_code__in=store_codes)

    # 操作日志（时间线）
    logs = OperationLog.objects.filter(task=task).order_by('created_at')

    return render(request, 'ops/task_detail.html', {
        'task':     task,
        'products': products,
        'stores':   stores,
        'logs':     logs,
    })


# ── 确认任务（AJAX POST）──

@login_required(login_url='/ops/')
def task_confirm(request, task_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    task = get_object_or_404(AgentTask, id=task_id)

    if task.status != AgentTask.Status.PENDING:
        return JsonResponse({'error': '只有待确认的任务可以确认'}, status=400)

    try:
        countdown = max(0, int((task.scheduled_at - timezone.now()).total_seconds()))

        if task.task_type == AgentTask.TaskType.PRODUCT_PUBLISH:
            from products.tasks import publish_products_task
            celery_task = publish_products_task.apply_async(
                args=[task.id], countdown=countdown
            )
        elif task.task_type == AgentTask.TaskType.STORE_DEACTIVATE:
            from stores.tasks import deactivate_stores_task
            celery_task = deactivate_stores_task.apply_async(
                args=[task.id], countdown=countdown
            )
        else:
            return JsonResponse({'error': '未知任务类型'}, status=400)

        task.status         = AgentTask.Status.CONFIRMED
        task.confirmed_by   = request.user.username
        task.celery_task_id = celery_task.id
        task.save()

        return JsonResponse({'success': True, 'message': f'任务已确认，将在 {task.scheduled_at} 执行'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ── 审计日志 ──

@login_required(login_url='/ops/')
def log_view(request):
    logs = OperationLog.objects.all().order_by('-created_at')[:200]
    return render(request, 'ops/log.html', {'logs': logs})


# ── 系统设置（只读展示）──

@login_required(login_url='/ops/')
def settings_view(request):
    import os
    context = {
        'email_address': os.getenv('EMAIL_ADDRESS', '未配置'),
    }
    return render(request, 'ops/settings.html', context)
