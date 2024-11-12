from django.test import TestCase
from django.apps import apps
from django.contrib.auth.models import Group, Permission

from asgiref.sync import sync_to_async

from api.relation import Relation
from api.local import LocalField
from api.base_rest import BaseREST
from api.filtersets import Filter, FilterURLBuilder


# Create your tests here.

class RestApiTest(TestCase):

    def setUp(self) -> None:
        self.group1 = Group(name= "group_test_A")
        self.group2 = Group(name= "group_test_B")
        Group.objects.bulk_create([self.group1, self.group2])
        class GroupRest(BaseREST):
            model = Group
            fields = {
                'id',
                'name',
                ('permissions',
                    ('id', 'codename',
                        ('content_type', ('model', 'id', 'app_label'))
                    )
                )
            }
            pass

        self.group_rest = GroupRest()
        return

    def test_validate_relations(self):
        assert self.group_rest.relations
        assert (m2m:= self.group_rest.relations['many_to_many'])
        assert len(m2m) == 2
        some1, some2 = m2m
        parent = some1.parent or some2.parent
        assert parent
        assert parent._field_name == 'permissions'
        assert parent.daughters
        assert parent.daughters.pop()._field_name == 'content_type'
        pass

    def test_validate_local_fields(self):
        assert len(local_fields:=self.group_rest.local_fields) == 2
        id=LocalField('id', Group)
        name= LocalField('name', Group)
        model_fields = [field.model_field for field in local_fields]
        assert id.model_field in model_fields and name.model_field in model_fields
        pass

    async def test_parse_objects(self):
        query_set = self.group_rest.build_query_relations(Group.objects).\
            filter(name__in=['group_test_A', 'group_test_B']).all()

        objects = await sync_to_async(list)(query_set)
        assert self.group1 in objects and self.group2 in objects
        parsed = await self.group_rest.parse_objects(objects)
        assert len(parsed) == 2
        for parsed_object in parsed:
            for field in self.group_rest.local_fields:
                assert parsed_object[field.name]

        pass

class TestFilterSetGroup(TestCase):

    def setUp(self) -> None:
        self.model = Group
        self.test_instance = Group(name='test group')
        self.test_instance.save()
        self.fake_get_params = (
            {'filterBy': 'name[exact]test group'},
            {'filterBy': 'name[exact]test group;pk[exact]%s'%self.test_instance.pk}
        )

    def test_just_one_filter_query_builder(self):
        url_filter = FilterURLBuilder(self.fake_get_params[0], self.model)
        filter =url_filter.build_node_filter()
        objects = self.model.objects.filter(filter).all()
        assert len(objects) <= 1
        assert self.test_instance.pk == objects[0].pk
        return

    def test_more_than_one_filter_query_builder(self):
        url_filter = FilterURLBuilder(self.fake_get_params[1], self.model)
        filter =url_filter.build_node_filter()
        objects = self.model.objects.filter(filter).all()
        assert len(objects) <= 1
        assert self.test_instance.pk == objects[0].pk
        return


class TestFilterSetPermissions(TestCase):

    def setUp(self) -> None:
        self.model = Permission
        self.fake_get_params = {'filterBy': 'content_type__model[iexact]USER'}
    pass

    def test_related_selections(self):
        query_filter = FilterURLBuilder(self.fake_get_params, self.model)
        filter = query_filter.build_node_filter()
        objects = self.model.objects.filter(filter).all()
        assert len(objects) <= 4
        return
    pass
