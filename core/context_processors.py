from django.conf import settings

def platform_settings(request):
    return {
        'PLATFORM': {
            'NAME': getattr(settings, 'PLATFORM_NAME', 'Ovinet'),
            'SUPPORT_EMAIL': getattr(settings, 'PLATFORM_SUPPORT_EMAIL', None),
            'SUPPORT_URL': getattr(settings, 'PLATFORM_SUPPORT_URL', None),
            'SUPPORT_PHONE': getattr(settings, 'PLATFORM_SUPPORT_PHONE', None),
            'LOGO_URL': getattr(settings, 'PLATFORM_LOGO_URL', None),
            'LOGO_ALT': getattr(settings, 'PLATFORM_LOGO_ALT', None),
        }
    }