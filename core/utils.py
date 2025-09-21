import re
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.cache import cache
from django.core.mail import send_mail
from django.template.loader import render_to_string


PHONE_RE = re.compile(r'^\\+?\d{7,15}$')


def validate_phone(value):
    if not PHONE_RE.match(value):
        raise ValidationError('Enter a valid phone number (international format).')
    


def human_readable_timedelta(td):
    # simple helper to present a timedelta as "1d 2h"
    total = int(td.total_seconds())
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days: parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    if seconds and not parts: parts.append(f"{seconds}s")
    return ' '.join(parts) or '0s'


def cache_get(key, default=None):
    return cache.get(key, default)


def cache_set(key, value, timeout=None):
    cache.set(key, value, timeout)


def cache_delete(key):
    cache.delete(key)
    

def cache_clear():
    cache.clear()
    
def send_templated_email(subject, template_name, context, recipient_list, from_email=None):
    body = render_to_string(template_name, context)
    send_mail(subject, body, from_email, recipient_list)