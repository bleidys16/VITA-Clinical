from rest_framework.permissions import BasePermission

class IsAdministrador(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'perfil') and request.user.perfil.rol == 'ADMIN'

class IsAnalista(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'perfil') and request.user.perfil.rol == 'ANALISTA'

class IsMedico(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'perfil') and request.user.perfil.rol == 'MEDICO'

class EsAdminOMedico(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'perfil') and request.user.perfil.rol in ('ADMIN', 'MEDICO')

class EsAdminOAnalista(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'perfil') and request.user.perfil.rol in ('ADMIN', 'ANALISTA')
