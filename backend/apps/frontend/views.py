from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache

@never_cache
def login_view(request):
    return render(request, 'login.html')

@never_cache
def dashboard_view(request):
    return render(request, 'dashboard.html')

@never_cache
def etl_view(request):
    return render(request, 'etl.html')

@never_cache
def pacientes_view(request):
    return render(request, 'pacientes.html')

@never_cache
def ml_modeling_view(request):
    return render(request, 'ml_modeling.html')

@never_cache
def analitica_view(request):
    return render(request, 'analitica.html')

@never_cache
def usuarios_view(request):
    return render(request, 'usuarios.html')
