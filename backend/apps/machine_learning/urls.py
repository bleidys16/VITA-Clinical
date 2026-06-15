from django.urls import path
from apps.machine_learning.views import TrainModelView, MetricasModeloMLView, PrediccionRiesgoView

urlpatterns = [
    path('train/', TrainModelView.as_view(), name='train-model'),
    path('model/metrics/', MetricasModeloMLView.as_view(), name='ml-metrics'),
    path('predict/', PrediccionRiesgoView.as_view(), name='ml-predict'),
]
