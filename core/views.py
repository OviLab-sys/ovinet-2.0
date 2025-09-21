from django.views.generic import TemplateView
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.shortcuts import render

@method_decorator(never_cache, name='dispatch')
class HomeView(TemplateView):
    template_name = 'core/home.html'

class PricingView(TemplateView):
    template_name = 'core/pricing.html'

class TermsView(TemplateView):
    template_name = 'core/terms.html'

class PrivacyView(TemplateView):
    template_name = 'core/privacy.html'

def handler404(request, exception):
    return render(request, 'core/404.html', status=404)

def handler500(request):
    return render(request, 'core/500.html', status=500)