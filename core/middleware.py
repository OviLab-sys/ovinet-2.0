from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import Http404


class TenantDetectionMiddleware(MiddlewareMixin):
    """Detect tenant from host and attach to request. In a django-tenants setup
    this would typically be handled by django-tenants middleware; this file
    provides a small helper you can extend.
    """
    def process_request(self, request):
        host = request.get_host().split(':')[0]
        request.tenant_host = host
        # optionally set request.tenant or similar