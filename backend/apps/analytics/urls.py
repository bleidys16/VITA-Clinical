from django.contrib import admin
from django.urls import path, include
from apps.analytics.views import DashboardKPIsView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/etl/', include('apps.etl.urls')),
    path('api/analytics/', include('apps.analytics.urls')), 
]