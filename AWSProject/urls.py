from django.contrib import admin
from django.urls import path,include
from django.conf import settings 
from django.conf.urls.static import static 
admin.site.login_url = settings.LOGIN_URL
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('PetStore.urls')), 
    path('my-admin/', include('Admin.urls')),  
    path('api/', include('APIs.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)