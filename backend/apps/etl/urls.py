# backend/apps/etl/urls.py

from django.urls import path
from .views import (
    RunETLView, ETLLogListView, ResetDataView, AuthMeView,
    ProfileUpdateView, DashboardDataView, ETLEstadoView, ReportesView,
    PacienteListView, PacienteCreateView, PacienteDetailView,
    UsuarioListView, UsuarioCreateView, UsuarioUpdateView, UsuarioDeleteView,
)

urlpatterns = [
    path('run/', RunETLView.as_view(), name='etl-run'),
    path('logs/', ETLLogListView.as_view(), name='etl-logs'),
    path('reset/', ResetDataView.as_view(), name='etl-reset'),
    path('auth/me/', AuthMeView.as_view(), name='etl-auth-me'),
    path('auth/profile/', ProfileUpdateView.as_view(), name='etl-profile'),
    path('analytics/dashboard/', DashboardDataView.as_view(), name='data-dashboard'),
    path('pacientes/', PacienteListView.as_view(), name='etl-pacientes'),
    path('pacientes/create/', PacienteCreateView.as_view(), name='paciente-create'),
    path('pacientes/<int:paciente_id>/update/', PacienteDetailView.as_view(), name='paciente-update'),
    path('pacientes/<int:paciente_id>/delete/', PacienteDetailView.as_view(), name='paciente-delete'),
    path('status/', ETLEstadoView.as_view(), name='etl-status'),
    path('reportes/', ReportesView.as_view(), name='etl-reportes'),
    path('usuarios/', UsuarioListView.as_view(), name='usuarios-list'),
    path('usuarios/create/', UsuarioCreateView.as_view(), name='usuarios-create'),
    path('usuarios/<int:user_id>/update/', UsuarioUpdateView.as_view(), name='usuarios-update'),
    path('usuarios/<int:user_id>/delete/', UsuarioDeleteView.as_view(), name='usuarios-delete'),
]