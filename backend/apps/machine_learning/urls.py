from django.urls import path
from apps.machine_learning.views import TrainModelView, MetricasModeloMLView, PrediccionRiesgoView, PrediccionPacienteView

urlpatterns = [
    path('train/', TrainModelView.as_view(), name='train-model'),
    path('model/metrics/', MetricasModeloMLView.as_view(), name='ml-metrics'),
    path('predict/', PrediccionRiesgoView.as_view(), name='ml-predict'),
    path('predict/paciente/<int:paciente_id>/', PrediccionPacienteView.as_view(), name='ml-predict-paciente'),
]
