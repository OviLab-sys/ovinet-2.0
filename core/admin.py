from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.models import Group, Permission

# Register platform-wide models



class CoreAdminSite(AdminSite):
    site_header = 'Ovinet Administration'
    site_title = 'Ovinet Admin'
    index_title = 'Platform Administration'


admin_site = CoreAdminSite(name='core_admin')

admin_site.register(Group)
admin_site.register(Permission)


# Optional: Custom admin views for platform management
@admin_site.register_view('platform-stats/', 'Platform Statistics')
def platform_stats_view(request):
    """Custom admin view for platform statistics"""
    from django.shortcuts import render
    context = admin_site.each_context(request)
    # Add your platform stats here
    return render(request, 'admin/platform_stats.html', context)