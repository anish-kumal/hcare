from django.shortcuts import render
from django.views.generic import TemplateView

# Create your views here.

class IndexView(TemplateView):
    """Render the home page"""
    template_name = 'index.html'
