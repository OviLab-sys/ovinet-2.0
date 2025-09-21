from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Platform Core'
    
    def ready(self):
        # Import admin to ensure registration happens
        import core.admin
        # Import signals if you have any
        # import core.signals