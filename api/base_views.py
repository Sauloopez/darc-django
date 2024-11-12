from django.views import View
from api.mixins import (
    BaseRESTGetMixin,
    BaseRESTPutMixin,
    BaseRESTPostMixin,
    BaseRESTPatchMixin,
    BaseRESTDeleteMixin
)

class GetRESTViewMixin(BaseRESTGetMixin, View):
    pass

class PostRESTViewMixin(BaseRESTPostMixin, View):
    pass

class PutRESTViewMixin(BaseRESTPutMixin, View):
    pass

class PatchRESTViewMixin(BaseRESTPatchMixin, View):
    pass

class DeleteRESTViewMixin(BaseRESTDeleteMixin, View):
    pass

class BaseRESTView(
    BaseRESTGetMixin,
    BaseRESTPostMixin,
    BaseRESTPutMixin,
    BaseRESTPatchMixin,
    BaseRESTDeleteMixin,
    View):
    pass
