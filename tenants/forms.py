from django import forms

class SessionPauseForm(forms.Form):
    PAUSE_REASON_CHOICES = [
        ('user_request', 'User Request'),
        ('admin_action', 'Admin Action'),
        ('system_auto', 'System Auto-pause'),
        ('payment_issue', 'Payment Issue'),
        ('other', 'Other'),
    ]

    pause_reason = forms.ChoiceField(
        choices=PAUSE_REASON_CHOICES,
        required=True,
        label="Pause Reason"
    )
    pause_description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label="Description (optional)"
    )