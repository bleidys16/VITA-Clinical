import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.test import RequestFactory
from apps.etl.views import ReportesView
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate

User = get_user_model()
user = User.objects.first()
print(f'User: {user}')

factory = APIRequestFactory()
request = factory.get('/api/etl/reportes/?format=csv', HTTP_ACCEPT='text/csv')
force_authenticate(request, user=user)
print(f'Auth: {request.user}, {request.auth}')

original_get = ReportesView.get
def debug_get(self, req, *args, **kwargs):
    print(f'GET called! args={args}, kwargs={kwargs}')
    print(f'format kwarg={kwargs.get("format")}')
    print(f'query params={dict(req.query_params)}')
    return original_get(self, req, *args, **kwargs)
ReportesView.get = debug_get

import rest_framework.views as rv
original_dispatch = rv.APIView.dispatch
def debug_dispatch(self, request, *args, **kwargs):
    print(f'dispatch called! path={request.path}, args={args}, kwargs={kwargs}')
    try:
        result = original_dispatch(self, request, *args, **kwargs)
        print(f'dispatch result status: {result.status_code}')
        return result
    except Exception as e:
        print(f'dispatch exception: {type(e).__name__}: {e}')
        raise
rv.APIView.dispatch = debug_dispatch

view = ReportesView.as_view(initkwargs={})
response = view(request)
print(f'Final Status: {response.status_code}')
print(f'Final Data: {response.data}')
