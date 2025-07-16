# myproject/blog/views.py

from django.shortcuts import render

def post_list(request):
    return render(request, 'index.html')