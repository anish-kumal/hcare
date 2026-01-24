from django import forms

from .models import AppointmentPayment


class AppointmentPaymentForm(forms.ModelForm):
    class Meta:
        model = AppointmentPayment
        fields = ['amount', 'payment_method', 'transaction_reference', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
            }),
            'payment_method': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
            }),
            'transaction_reference': forms.TextInput(attrs={
                'placeholder': 'Transaction ID / Receipt Number',
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Optional payment notes',
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
            }),
        }
