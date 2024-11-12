from asyncio.tasks import gather
from typing import Literal, Self, Union
from asgiref.sync import sync_to_async
from django.db.models import Model, ForeignKey, ObjectDoesNotExist, OneToOneField, ManyToManyField
from django.db.models.fields.reverse_related import OneToOneRel, ManyToOneRel, ManyToManyRel, ForeignObjectRel
from django.db.models.fields.related_descriptors import (
    ForwardOneToOneDescriptor,
    ForwardManyToOneDescriptor,
    ReverseOneToOneDescriptor,
    ReverseManyToOneDescriptor,
    ManyToManyDescriptor,
)
from api import exceptions, local

forward_descriptors= (ForwardOneToOneDescriptor,ForwardManyToOneDescriptor)
reverse_descriptors= (ReverseOneToOneDescriptor,ReverseManyToOneDescriptor)
all_descriptors= (*forward_descriptors, *reverse_descriptors)
M2O = 'many_to_one'; O2O='one_to_one'; M2M='many_to_many';O2M='one_to_many'
boolean_field_relations = (M2O, O2O, M2M, O2M)

# relation with select related: many_to_one and one_to_one
# relation with prefetch related: many_to_many and one_to_many

class Relation:

    def __init__(
        self,
        direction: type[Model],
        field_name: str,
        parent: Self| None = None,
        relation_fields: set[local.LocalField] | None = None
    ) -> None:
        self.is_parsed = False
        self._direction = direction
        self._field_name = field_name
        self.relation_fields = relation_fields
        self.daughters : set[Self] = set()
        descriptor = getattr(direction, field_name, None)
        if not descriptor:
            raise Exception('Unavailable access to descriptor on {}->{}'.format(
                self._direction._meta.model_name,
                field_name)
            )
        self._descriptor: Union[
            ForwardOneToOneDescriptor,
            ForwardManyToOneDescriptor,
            ReverseOneToOneDescriptor,
            ReverseManyToOneDescriptor,
            ManyToManyDescriptor
        ] = descriptor
        model_field = None
        if isinstance(self._descriptor, reverse_descriptors):
            relation = (
                getattr(self._descriptor, 'related', None) or
                getattr(self._descriptor, 'rel', None)
            )
            model_field = relation
        elif isinstance(self._descriptor, forward_descriptors):
            model_field = self._descriptor.field
        if not model_field:
            raise Exception('Impossible find the model field in relation {}->{}'.format(
                    self._direction._meta.model_name,
                    field_name
                )
            )
        if not model_field.is_relation:
            raise exceptions.InvalidRelationField(model_field.name)
        self._model_field = model_field
        self._related_model = self._model_field.related_model
        if self._related_model == self._direction:
            self._related_model = self._model_field.model

        self._relation_name = '%s__%s'%(parent, field_name) if parent else field_name
        self._parent = parent

        if parent is not None:
            parent.add_daughter(self)
            if parent.type in boolean_field_relations[2:]:
                self._relation_type = parent.type
                return
        found_rel = False
        possible_relation = None
        for possible_relation in boolean_field_relations:
            if found_rel := getattr(model_field, possible_relation, False):
                break
        if not found_rel or not possible_relation:
            raise Exception('Impossible find the relation in field %s'%model_field)
        self._relation_type = possible_relation

        return

    @property
    def type(self)-> Union[
        Literal['many_to_one'],
        Literal['one_to_one'],
        Literal['many_to_many'],
        Literal['one_to_many'],
    ]:
        """
        The type of the relation.
        """
        return self._relation_type

    @property
    def from_m(self):
        return self._direction

    @property
    def to_m(self):
        return self._related_model

    @property
    def parent(self):
        return self._parent

    @property
    def is_to_many(self):
        return getattr(self._model_field, M2M, False) or getattr(self._model_field, O2M, False)

    @property
    def is_to_one(self):
        return getattr(self._model_field, M2O, False) or getattr(self._model_field, O2O, False)

    def __str__(self) -> str:
        return self._relation_name

    def __repr__(self) -> str:
        return f'<{self._relation_name}: {self.relation_fields}>'

    def add_daughter(self, relation: Self):
        self.daughters.add(relation)

    def get_related_fk(self, value):
        return self._related_model(**{self._model_field.target_field.name: value})

    def parse_instance_data(self, model_instance, /):
        if model_instance is None:
            return None
        if not self.relation_fields: return {}
        parsed_object = {}
        for local_field in self.relation_fields:
            parsed_object[local_field.name] = getattr(model_instance, local_field.name)
        return parsed_object

    async def __get_daughter_relations_data(self, model_instance):
        return await gather(*[
            daughter.get_relation_data(model_instance)
            for daughter in self.daughters
        ])

    async def get_relation_data(self, model_instance):
        try:
            manager = await sync_to_async(getattr)(model_instance, self._field_name)
        except ObjectDoesNotExist:
            return {self._field_name: None}

        parsed_object = None
        if getattr(self._model_field, O2M, False) or \
            getattr(self._model_field, M2M, False): # if my native field is to many
            parsed_object = []
            items = await sync_to_async(list)(manager.all()) # recovery all items
            for item in items: # for each item..
                parsed_data = self.parse_instance_data(item) # parse local info
                relations = await self.__get_daughter_relations_data(item)
                for relation in relations:
                    parsed_data |= relation
                parsed_object.append(parsed_data)
        elif getattr(self._model_field, M2O, False) or \
            getattr(self._model_field, O2O, False): # if my native field is to one
            parsed_object = {}
            if parsed_data:= self.parse_instance_data(manager): # recovery the info with the manager
                relations = await self.__get_daughter_relations_data(manager)
                for relation in relations:
                    parsed_data |= relation
                parsed_object |= parsed_data

        return {self._field_name: parsed_object or None}

    pass


class RelationManager:

    def __init__(self) -> None:
        self._relations: dict[Union[
            Literal['many_to_one'],
            Literal['one_to_one'],
            Literal['many_to_many'],
            Literal['one_to_many'],
        ], set[Relation]] = {}
        pass

    @property
    def relations(self):
        return self._relations

    @property
    def selecting_relations(self)-> set[Relation]:
        return {
            *self['many_to_one'],
            *self['one_to_one']
        }

    @property
    def prefetching_relations(self)-> set[Relation]:
        return {
            *self['many_to_many'],
            *self['one_to_many']
        }

    @property
    def related_selections(self):
        if rss:=self.selecting_relations:
            return set(str(rs) for rs in rss)
        return set()

    @property
    def prefetch_selections(self):
        if pss:=self.prefetching_relations:
            return set(str(ps) for ps in pss)
        return set()

    def __getitem__(self, key):
        try:
            return self._relations[key]
        except KeyError:
            return []

    def __iter__(self):
        if getattr(self, '_rel_vector', None) is None:
            self._rel_vector: set[Relation] = set()
            for relation_type in self._relations.values():
                self._rel_vector |= relation_type
        self._iter = iter(self._rel_vector)
        return self

    def __next__(self):
        if self._iter is None:
            raise StopIteration()
        try:
            return next(self._iter)
        except StopIteration:
            self._iter = None
            raise

    def add(self,relation: Relation):
        try:
            self._relations[relation.type].add(relation)
        except KeyError:
            self._relations[relation.type] = {relation}
        return
    pass

__all__= ['Relation', 'RelationManager']
