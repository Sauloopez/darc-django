from typing import Self
from typing_extensions import Literal
from django.db.models import Q
from api.local import LocalField
import re

"""
Goal:
    /my/url/path/?filterBy=!field_name[OP]value;

    in keys [] is the OPERATOR
    fieldname is the field to filter
    ! for negate the filter
    comma ',' for OR and dot and comma ';' for AND operator inner filter
"""

OPERATORS = {
    'exact': '__exact',
    'iexact': '__iexact',
    'contains':'__contains',
    'icontains': '__icontains',
    'in': '__in',
    'startswith': '__startswith',
    'istartswith': '__istartswith',
    'endswith': '__iendswith',
    'year': '__year',
    'date':'__date',
    'iso_year': '__iso_year',
    'range': '__range',
    'gte': '__gte',
    'lte': '__lte',
    'gt': '__gt',
    'lt': '__lt',
}

class Filter(Q):

    def __init__(
        self,
        field_name,
        value,
        operator:str='exact',
        _connector=None,
        _negated=False
    ):
        self._field_name = field_name
        self.value = value
        try:
            self._operator = OPERATORS[operator]
        except KeyError:
            raise Exception('Loookup operator unbound')
        self.lookup = '%s%s'%(self._field_name, self._operator)
        super().__init__(_connector=_connector, _negated=_negated, **{self.lookup: self.value} )
        return
    pass


class FilterURLBuilder:

    __REGEX = re.compile(r'(?P<negate>!?)(?P<field>[a-zA-Z_][a-zA-Z0-9_]*)\[(?P<operator>[a-zA-Z]+)\](?P<value>[^;,]+)(?P<sep>[;,]?)')

    def __init__(self, request_get_params, model, key_param = 'filterBy') -> None:
        self.model = model
        self.query_string: str = request_get_params.get(key_param, None)
        if not self.query_string:
            return
        pass

    def build_node_filter(self)-> Filter | None:
        if not self.query_string:
            return None
        filter_qs: Filter = None
        current_filter = None
        before_xpr = None
        for match in self.__REGEX.finditer(self.query_string):
            negate = True if match.group('negate') else False
            field_name = match.group('field')
            operator = match.group('operator')
            value = match.group('value')
            separator = match.group('sep')
            current_filter = Filter(
                field_name,
                value,
                operator,
                _negated=negate
            )
            if before_xpr is not None and filter_qs:
                sep, before_filter = before_xpr
                if sep == ';':
                    filter_qs &= current_filter
                if sep == ',':
                    filter_qs |= current_filter
            before_xpr = (separator, current_filter)
            if filter_qs is None:
                filter_qs = current_filter
                continue

        return filter_qs

    pass
