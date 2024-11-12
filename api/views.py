from django.http.response import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie


# Create your views here.
@ensure_csrf_cookie
async def root(req):
    return JsonResponse(
        {'message': 'ok'},
        status=200
        )
