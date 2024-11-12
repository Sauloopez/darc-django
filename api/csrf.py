from functools import wraps

from django.middleware.csrf import get_token
from django.http import HttpRequest, HttpHeaders, HttpResponse
from django.conf import settings



def ensure_csrf_header(view_func):

    @wraps(view_func)
    async def wrapper(request: HttpRequest, *args, **kwargs):
        res: HttpResponse= await view_func(request, *args, **kwargs)
        try:
            csrf_header = HttpHeaders.parse_header_name(settings.CSRF_HEADER_NAME)
            res[csrf_header] = request.META['CSRF_COOKIE']
            return res
        except KeyError:
            raise Exception('Bad configured. Must be exists csrf cookie before call')
    return wrapper
