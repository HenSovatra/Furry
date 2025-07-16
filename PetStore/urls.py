# myproject/blog/urls.py

from django.urls import path
from . import views # Import views from the current app

app_name = 'PetStore' 

urlpatterns = [
    path('', views.post_list, name='list'), 
]