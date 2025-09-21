from django import template
from django.utils.html import format_html


register = template.Library()


@register.simple_tag
def platform_name():
    return 'Ovinet'


@register.simple_tag
def mailto(email, label=None):
    label = label or email
    return format_html('<a href="mailto:{}">{}</a>', email, label)