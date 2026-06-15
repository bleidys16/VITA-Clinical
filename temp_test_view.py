import sys, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.test import RequestFactory
from apps.etl.views import ReportesView
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from apps.etl.models import Paciente

User = get_user_model()
user = User.objects.first()
print(f'User: {user}')
print(f'Patients: {Paciente.objects.count()}')

factory = APIRequestFactory()
request = factory.get('/api/etl/reportes/?format=csv')
force_authenticate(request, user=user)

print(f'Query params: {request.query_params}')

view = ReportesView.as_view()
response = view(request)
print(f'Status: {response.status_code}')
print(f'Headers: {dict(response.items())}')
if hasattr(response, 'data'):
    print(f'Data: {response.data}')
import io
print(f'Content: {response.content[:200]}')
