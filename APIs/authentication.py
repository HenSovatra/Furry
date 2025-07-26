
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import AnonymousUser
from Admin.models import AccessToken
from django.contrib.auth import get_user_model
from django.conf import settings

class QueryParamAccessTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        access_token = request.query_params.get('access_token')

        if not access_token:
            return None 

        User = get_user_model()
        if access_token == settings.DEMO_API_ACCESS_TOKEN:
            try:
                user = User.objects.get(username='api_user')
            except User.DoesNotExist:
                user = User.objects.create_user(username='api_user', email='api@example.com', password='some_random_password')
                user.is_active = True
                user.save()
            return (user, None)
        else:
            raise AuthenticationFailed('Invalid access token.')

    def authenticate_header(self, request):
        return 'X-Access-Token realm="API"'
