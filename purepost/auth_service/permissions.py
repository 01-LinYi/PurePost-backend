from rest_framework import permissions

class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj == request.user

class IsAdminUser(permissions.BasePermission):
    message = "Only admin users can access this resource."
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_admin)

class IsSuperUser(permissions.BasePermission):
    message = "Only superusers can access this resource."
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)