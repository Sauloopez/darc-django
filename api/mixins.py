from django.core.exceptions import FieldError
from django.db.models import Model
from django.http import HttpRequest, JsonResponse
from asgiref.sync import sync_to_async
from typing import Literal
from api.base_rest import BaseREST
from . import exceptions, utils
from .async_transaction import async_atomic

class BaseRESTGetMixin(BaseREST):

    async def get(self, request : HttpRequest, *args, **kwargs):
        response = None
        try:
            if self.allow_only_fields:
                of_str = request.GET.get('onlyFields', None)
                if of_str and not isinstance(of_str, str):
                    of_str=str(of_str)
                only_fields = self.resolve_only_fields(
                    of_str
                )
                if only_fields:
                    self.initialize_fields(only_fields)
            if pk := kwargs.get('id', None):
                return await self.retrieve(pk)
            query = self.build_query_relations(self.model.objects)
            if filter_query:= self.get_filter_from_request(request):
                query = query.filter(filter_query)
            objects = await sync_to_async(list)(query.all())
            parsed_objects = await self.parse_objects(objects)
            if self.allow_pagination:
                parsed_objects = self.resolve_pagination(request, parsed_objects)
            del objects, query
            response = JsonResponse(parsed_objects, safe=False)
        except exceptions.ObjectDoesNotExist:
            response = JsonResponse({'message': 'not found'}, status=404)
        except (
            exceptions.FieldNotInModel,
            exceptions.MultipleLevelRelation,
            exceptions.FieldIsPrivated
        ) as exp:
            response = JsonResponse({'message': exp.message}, status=400)
        except FieldError:
            response = JsonResponse(
                {'message': 'The provided fields for retrive, '\
                    'aren\'t available in the resource'},
                status=400
            )
        return response
    pass

class BaseRESTPostMixin(BaseREST):

    @utils.validate_json_request_body
    @utils.validate_data_fields()
    async def post(self, request: HttpRequest, *args, **kwargs):
        data = request.json_data
        body_response = {}
        response = None
        status=200
        object_instance = self.model()
        self._update_local_fields_in_model_instance(object_instance, data)
        _, gather_coroutine = self._update_relation_fields_in_model_instance(object_instance, data)
        presave_action = getattr(self, 'pre_save', None)
        if presave_action:
            object_instance = presave_action(request, object_instance, *args, **kwargs)
        try:
            async with async_atomic():
                await object_instance.asave()
                if gather_coroutine:
                    await gather_coroutine
                object_instance = await self.build_query_relations(self.model.objects).aget(pk=object_instance.pk)
            body_response['message'] = f"{object_instance} has been saved sucessfully"
            parsed_object = await self.parse_object(object_instance)
            body_response['object'] = parsed_object
        except (
            exceptions.IntegrityError,
            exceptions.Empty2MRelationKeys,
            exceptions.Some2MRelationalsDoesNotExists,
            exceptions.EmptyToObjectsForRelate,
            exceptions.InvalidToObjectsForRelate,
            exceptions.InvalidRelationField,
            exceptions.Invalid2ManyRelationMode,
            exceptions.ObjectToRelateDoesNotExists,
        ) as exp:
            status=400
            body_response['error'] = str(exp)
        return JsonResponse(body_response, status = status)
    pass

class BaseRESTPutMixin(BaseREST):

    @utils.validate_json_request_body
    @utils.validate_updatable_fields()
    @BaseREST.validate_pk_provided
    async def put(self, request: HttpRequest, *args, **kwargs):
        return await self.dispatch_update(request.json_data, kwargs.get('id'), False)
    pass

class BaseRESTPatchMixin(BaseREST):
    @utils.validate_json_request_body
    @BaseREST.clean_possible_fields
    @BaseREST.validate_pk_provided
    async def patch(self, request : HttpRequest, *args, **kwargs):
        return await self.dispatch_update(request.json_data, kwargs.get('id'))
    pass

class BaseRESTDeleteMixin(BaseREST):

    @utils.parse_possible_json_data
    @utils.validate_possible_json_keys(['pks'])
    async def delete(self, request: HttpRequest, *args, **kwargs):
        if json_data:=getattr(request, 'json_data', None):
            return await self.bulk_delete(json_data['pks'])
        if not (pk := kwargs.get('id', None)):
            return JsonResponse({'message': 'Must be exists identifier on GET or pks in JSON'}, status=400)
        return await self.bulk_delete([pk])
    pass

__all__ = [
    'BaseRESTGetMixin',
    'BaseRESTPostMixin',
    'BaseRESTPutMixin',
    'BaseRESTPatchMixin',
    'BaseRESTDeleteMixin',
]
