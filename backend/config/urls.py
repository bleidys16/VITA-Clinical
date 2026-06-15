from django.contrib import admin
from django.urls import path, include
from apps.analytics.views import DashboardKPIsView
from apps.machine_learning.views import MetricasModeloMLView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/etl/', include('apps.etl.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
    path('api/ml/', include('apps.machine_learning.urls')),
    path('api/predicciones/', MetricasModeloMLView.as_view(), name='api-predicciones'),
    path('api/dashboard/kpis/', DashboardKPIsView.as_view(), name='dashboard-kpis'),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include('apps.frontend.urls')),
]