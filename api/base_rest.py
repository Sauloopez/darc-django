from asyncio import gather
from types import NoneType
from typing import Literal
from django.http import HttpRequest, JsonResponse
from django.db.models import Model, QuerySet

from api.async_transaction import async_atomic
from api.pagination import Pagination
from api.relation import Relation, RelationManager
from api.local import LocalField
from api.filtersets import FilterURLBuilder
from api import exceptions, utils, base_responses

class BaseREST:
    """
    Main functionalities for build a full async API RESTful for make CRUD in a Django model.
    """
    model : type[Model]
    """
    The model for make the API REST CRUD
    """
    allow_only_fields = True
    """
    Allows `onlyFields` in GET request URL param for just some fields.
    """
    allow_pagination = True
    """
    Allows the pagination for this API rest with `itemsPerPage` and `pages` in GET request URL params.
    """
    fields: Literal['__all__'] | set[str | tuple[str, tuple]]
    """
    fields = {
        'field1',
        'field2',
        ('field3': ['field3.1', 'field3.2']),
    }
    """
    nonupdatable_fields: set[str]= set()
    """
    Set of static fields. Default empty.
    """
    filter_url_param = 'filterBy'
    """
    The GET request URL parameter for filter.
    `filterBy` as default.
    """
    privated_fields: set[str]= set()
    """
    Set of fields that will not be represented in the responses.
    Can be empty.
    """

    def __init__(self, **kwargs) -> None:
        if not self.model or not self.fields:
            raise Exception('model and fields is required')
        self.initialize_fields(self.fields)
        return

    def initialize_fields(self, fields):
        """
        Initialize the fields for works the model instances with relations and local changes.
        """
        # the model fields that can't be empty or null
        self.required_model_fields = utils.get_required_model_fields(self.model)
        # the defined field names in the model
        self.model_fields = utils.get_model_fields(self.model)
        self.optional_model_fields = set(self.model_fields) - set(self.required_model_fields)
        # fields validation obtains the relations and the local fields
        # this last, are the fields that doesn't express a relation
        self.relations, self.local_fields = self.validate_fields(fields)
        self.related_selections = set()
        self.prefetch_selections = set()
        if not self.relations:
            return
        # set of full relation's key names for call with joins in select_related
        self.related_selections = self.relations.related_selections
        # set of full relation's key names for call in 'prefetch_related'
        self.prefetch_selections = self.relations.prefetch_selections
        return

    def validate_fields(
        self,
        fields: set[str] | set[tuple[str, list[str]]] | str,
        model = None,
        relations: RelationManager | None = None,
        parent_relation: Relation | None = None,
    ) -> tuple[RelationManager | None, set[LocalField]]:
        """
        Build recursively the local fields and relations with the set data structure named `fields`.
        """
        model_fields = None
        if model == None:
            model = self.model
            model_fields = self.model_fields
        if not model_fields:
            model_fields = utils.get_model_fields(model)
        if relations is None:
            relations = RelationManager()
        if isinstance(fields, str):
            if fields == '__all__':
                return self.validate_fields(model_fields)
        _fields = set()
        if isinstance(fields, set):
            for field in fields:
                if isinstance(field, tuple):
                    related_field, related_fields = field
                    relation= Relation(model, related_field, parent_relation)
                    _, relation_fields = self.validate_fields(
                        set(related_fields),
                        relation.to_m,
                        relations,
                        relation
                    )
                    relation.relation_fields= relation_fields
                    relations.add(relation)
                    continue
                if isinstance(field, str):
                    if field in self.privated_fields:
                        raise exceptions.FieldIsPrivated(field)
                    if field == '__all__':
                        _, ml_fields = self.validate_fields(
                            model_fields,
                            model,
                            relations,
                            parent_relation
                        )
                        _fields|=ml_fields
                        continue
                    try:
                        _fields.add(LocalField(field, model))
                    except exceptions.LocalFieldIsDescriptor:
                        pass
                    continue
                raise exceptions.InvalidFieldFormat(field)
            return relations or None, _fields
        raise Exception('fields is not valid, must be a set or a string')

    def resolve_pagination(self, request : HttpRequest, objects : list):
        pagination = Pagination(objects)
        if pages := int(request.GET.get('pages', 0)):
            pagination.with_num_pages(pages)
        if items_per_page := int(request.GET.get('itemsPerPage', 0)):
            pagination.with_items_per_page(items_per_page)

        return pagination.pages or objects

    def build_query_relations(self, initial_query: QuerySet):
        initial_query= self.__build_q_related_selections(initial_query)
        return self.__build_q_prefetched_selections(initial_query)

    def __build_q_related_selections(self, initial_query: QuerySet):
        if self.related_selections:
            initial_query = initial_query.select_related(*self.related_selections)
        return initial_query

    def __build_q_prefetched_selections(self, initial_query: QuerySet):
        if self.prefetch_selections:
            initial_query = initial_query.prefetch_related(*self.prefetch_selections)
        return initial_query

    async def retrieve(self, pk):
        object_ = await self.build_query_relations(self.model.objects).aget(pk = pk)
        parsed_object = await self.parse_object(object_)
        return JsonResponse(parsed_object)

    async def parse_objects(self, objects):
        return [await self.parse_object(obj) for obj in objects]

    async def parse_object(self,
        model_instance,
        fields: set[LocalField] | None = None,
    ):
        parsed_object = self.parse_local_fields(model_instance)
        await self.parse_relations(model_instance, parsed_object)
        return parsed_object

    async def parse_relations(self, model_instance, parsed_object: dict):
        if not self.relations:
            return parsed_object

        related = {}

        for relation in self.relations:
            if not relation.parent:
                parsed_object |= await relation.get_relation_data(model_instance)
        return parsed_object

    def parse_local_fields(
        self,
        model_instance,
        fields: set[LocalField] | None = None
    ):
        parsed_object = {}
        if fields is None:
            fields = self.local_fields
        for field in fields:
            value = getattr(model_instance, field.name)
            parsed_object[field.name] = value
            if not isinstance(value, (str, int, float, bool, NoneType)):
                parsed_object[field.name] = str(value)
        return parsed_object


    def resolve_only_fields(self, only_fields : str | None = None):
        """
        Resolve the fields to be included in the response.

        If `only_fields` is None, it will return None.
        If `only_fields` is '__all__', it will return the validated fields of the model.
        If `only_fields` is a string, it will be split by commas and each field will be processed.

        Returns:
            list: A list of fields to be included in the response.
        """
        if not only_fields:
            return None
        if only_fields == '__all__':
            return self.model_fields
        fields = set()
        relations = {}
        # sepparated comma fields
        sprtd_cmm_flds = only_fields.split(',')

        for formated_field in sprtd_cmm_flds:
            if '.' in formated_field:
                try:
                    relation_name, related_field = formated_field.split('.')
                except ValueError:
                    raise exceptions.MultipleLevelRelation(formated_field)
                if related_field == '__all__':
                    relations[relation_name] = related_field
                    continue
                if relations.get(relation_name):
                    relations[relation_name].append(related_field)
                else:
                    relations[relation_name] = [related_field]
                continue
            fields.add(formated_field)
        for relation_name, relation_fields in relations.items():
            fields.add((relation_name, tuple(relation_fields)))
        del relations, sprtd_cmm_flds
        return fields

    def _clean_relations_in_data(self, data :dict):
        _data = data.copy()
        if not self.relations:
            return data, {}
        related_names = {}
        value = None
        for relation in self.relations:
            if not relation.parent and relation._field_name in data:
                if relation.type in ('many_to_many', 'one_to_many'):
                    related_names[relation._field_name] = data[relation._field_name]
                    del _data[relation._field_name]
                if relation.type in ('one_to_one', 'many_to_one'):
                    _data[relation._field_name] = \
                        relation.get_related_fk(_data[relation._field_name])
        return _data, related_names

    def validate_pk_provided(view_func):
        async def wrapper(*args, **kwargs):
            pk = kwargs.get('id', None)
            if not pk:
                return JsonResponse({'error': 'No identificator provided'}, status=400)
            return await view_func(*args, **kwargs)
        return wrapper

    # TODO: creation of a model instance
    async def _create_model_instance(self, data: dict):
        pass

    async def dispatch_update(self, data: dict, pk, clean=True):
        status = 200
        body_response = {}
        try:
            body_response= await self._update_model_instance(pk, data, clean)
        except exceptions.ObjectDoesNotExist:
            body_response['error'] = f'The requested object identified by {pk} does not exists'
            status = 404
        except exceptions.IntegrityError as exp:
            body_response['error'] = str(exp)
            status = 400
        except (
            exceptions.Empty2MRelationKeys,
            exceptions.Some2MRelationalsDoesNotExists,
            exceptions.EmptyToObjectsForRelate,
            exceptions.InvalidToObjectsForRelate,
            exceptions.InvalidRelationField,
            exceptions.Invalid2ManyRelationMode,
            exceptions.ObjectToRelateDoesNotExists,
        ) as exp:
            body_response['error'] = exp.message
            status = 400
        return JsonResponse(body_response, status=status)

    def get_filter_from_request(self, request: HttpRequest):
        if not request.method == 'GET':
            return
        query_filter= FilterURLBuilder(request.GET, self.model, self.filter_url_param)
        return query_filter.build_node_filter()

    async def _update_model_instance(self, pk, data: dict, clean = True):
        update_body={}
        # build query for retrieve the object
        queryset = self.build_query_relations(self.model.objects)
        #retrieve the model instance identified by pk
        model_instance = await queryset.aget(pk=pk)
        # update the local attributes
        local_fields_updated = self._update_local_fields_in_model_instance(model_instance, data, clean)
        # promove the relations in a gather
        relations_updated, gather_coroutine = self._update_relation_fields_in_model_instance(model_instance, data)
        gathering_process = []
        if local_fields_updated or relations_updated:
            gathering_process.append(model_instance.asave(force_update=True))
        if gather_coroutine:
            gathering_process.append(gather_coroutine)
        if gathering_process:
            #in an atomic...
            async with async_atomic():
                # save the model instance
                await gather(*gathering_process)
            update_body['message'] = f'\'{model_instance}\' updated sucessfully'
            update_body['observation'] = f'Fields updated: {local_fields_updated | relations_updated}'
        else:
            update_body['message'] = 'Nothing for update'
        parsed_object = await self.parse_object(model_instance, self.local_fields)
        update_body['object'] = parsed_object
        del model_instance
        return update_body

    def _update_local_fields_in_model_instance(self, model_instance, data: dict, clean = True):
        fields_updated = set()
        for local_field in self.local_fields:
            if local_field.name in data and \
                not local_field._model_field.primary_key and \
                (not clean or \
                    getattr(model_instance, local_field.name) != data[local_field.name]):
                setattr(model_instance, local_field.name, data[local_field.name] or None)
                fields_updated.add(local_field.name)
        return fields_updated

    def __get_async_function_r_manager(self, relation: Relation, model_instance, relation_data: dict | list):
        r_manager = getattr(model_instance, relation._field_name, None)
        valid_modes = 'add', 'set', 'remove'
        if not r_manager:
            return
        async_func = None
        if isinstance(relation_data, list):
            return r_manager.aset(relation_data)
        if isinstance(relation_data, dict):
            if not (to_rel:=relation_data.get('to', None)):
                raise exceptions.EmptyToObjectsForRelate(relation._field_name)
            if not isinstance(to_rel, list):
                raise exceptions.InvalidToObjectsForRelate(relation._field_name)
            mode= relation_data.get('mode', None) or 'set'
            if not mode in valid_modes:
                raise exceptions.Invalid2ManyRelationMode(mode, valid_modes, relation._field_name)
            async_func = getattr(r_manager, 'a%s'%mode)
            if mode != valid_modes[1]:
                return async_func(*to_rel)
            return async_func(to_rel)
        raise exceptions.Invalid2ManyRelationFormat(relation_data)

    def _update_relation_fields_in_model_instance(self, model_instance, data: dict):
        relations_updated = set()
        gathered_process = []
        gather_rel = None
        if not self.relations:
            return relations_updated, gather_rel
        for relation in self.relations:
            if relation.parent or relation._field_name not in data:
                continue
            if relation.is_to_many:
                async_func = self.__get_async_function_r_manager(
                    relation, model_instance, data[relation._field_name]
                )
                gathered_process.append(async_func)
            if relation.is_to_one:
                if isinstance((value:=data[relation._field_name]), (str, int)):
                    original_value = relation._model_field.value_from_object(model_instance)
                    if original_value == value:
                        continue
                    setattr(
                        model_instance,
                        relation._field_name,
                        relation.get_related_fk(value)
                    )
                    gathered_process.append(
                        self.assign_related_data(
                            model_instance,
                            relation._field_name,
                            relation.get_related_fk(value)
                        )
                    )
            relations_updated.add(relation._field_name)

        if gathered_process:
            gather_rel = gather(*gathered_process)
        return relations_updated, gather_rel

    async def assign_related_data(self, model_instance, field_name, value):
        try:
            value = await value._meta.model.objects.aget(pk=value.pk)
            setattr(model_instance, field_name, value)
        except exceptions.ObjectDoesNotExist:
            raise exceptions.ObjectToRelateDoesNotExists(field_name, value.pk)

    def clean_possible_fields(view_func):
        async def wrapper(self: 'BaseREST', *args, **kwargs):
            req=args[0]
            if isinstance(req, HttpRequest):
                if not (json_data:=getattr(req, 'json_data')):
                    return base_responses.no_request_body_response
                related_fields = self.related_selections | self.prefetch_selections
                all_fields = related_fields.union(self.model_fields)
                invalid_keys = [f for f in json_data.keys() if f not in all_fields]
                if invalid_keys:
                    return base_responses.invalid_fields_response(invalid_keys)
                return await view_func(self, *args, **kwargs)
        return wrapper

    async def bulk_delete(self, pks : list, model = None):
        if not model:
            model = self.model
        response_body = {}
        status = 200
        try:
            deletions, _ = await model.objects.filter(pk__in=pks).adelete()
            if not deletions:
                response_body['error']= 'Impossible delete element(s) identified by: %s'%str(pks)
                status = 404
            else:
                response_body['message'] = 'Elements identified by %s deleted sucessfully'%str(pks)
                if deletions < len(pks):
                    response_body['message'] = 'Some elements identified in %s deleted sucessfully'%str(pks)
                    response_body['observation'] = 'Some elements in %s does not exists'%str(pks)
        except exceptions.IntegrityError as exp:
            response_body['error']= 'Impossible delete element(s) identified by: %s. Error: %s'%(str(pks), str(exp))
            status=500
        return JsonResponse(response_body, status=status)
    pass
