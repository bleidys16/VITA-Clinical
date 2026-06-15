from django.urls import path
from apps.analytics.views import DashboardKPIsView, DescriptiveAnalyticsView

urlpatterns = [
    path('kpis/', DashboardKPIsView.as_view(), name='dashboard-kpis'),
    path('descriptiva/', DescriptiveAnalyticsView.as_view(), name='analytics-descriptiva'),
]
