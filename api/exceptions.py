from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import IntegrityError

class BaseException(Exception):
    def __init__(self, msg : str, *args) -> None:
        super().__init__(*args)
        self.message = msg
        return

    def __str__(self) -> str:
        return self.message
    pass

class InvalidRelationField(BaseException):

    def __init__(self, field_name : str, *args) -> None:
        super().__init__(f'{field_name} is not a relation field', *args)
    pass

class FieldNotInModel(BaseException):

    def __init__(self, field_name : str, model_name : str, *args) -> None:

        super().__init__(
            '\'%s\' is not a valid field in relation \'%s\''%
            (field_name, model_name),
            *args
        )
    pass

class InvalidFieldFormat(BaseException):

    def __init__(self, expression, *args) -> None:
        super().__init__(f'Invalid format for field expression: {expression}', *args)
        return
    pass

class MultipleLevelRelation(BaseException):

    def __init__(self, expression, *args) -> None:
        super().__init__(f'Multiple relation level in expression \'{expression}\'', *args)
        return
    pass

class Some2MRelationalsDoesNotExists(BaseException):

    def __init__(self, relations : list | str, *args) -> None:
        super().__init__(
            f'Some identifiers of {relations} does not exists',
            *args
        )
        return
    pass

class Empty2MRelationKeys(BaseException):

    def __init__(self, relation_field : str, *args) -> None:
        super().__init__(
            f'The relational keys in {relation_field} are empty',
            *args
        )
        return
    pass

class InvalidValueInRelationKey(BaseException):

    def __init__(self, relation_field : str, *args) -> None:
        super().__init__(f'the type values provided in {relation_field} is invalid', *args)
        return
    pass


class EmptyToObjectsForRelate(BaseException):

    def __init__(self, relation_name: str, *args) -> None:
        super().__init__('No \'to\' objects for relate in %s'%relation_name, *args)
        return
    pass


class InvalidToObjectsForRelate(BaseException):

    def __init__(self, relation_name: str, *args) -> None:
        super().__init__('\'to\' objects in %s must be a pk identifiers'%relation_name, *args)
        return
    pass

class Invalid2ManyRelationMode(BaseException):

    def __init__(self, mode_supplied, valid_modes, relation_name, *args) -> None:
        super().__init__(f'Invalid relation mode \'{mode_supplied}\' in {relation_name}.'\
        f'Valid are {valid_modes}. Default: set', *args)
        return
    pass

class Invalid2ManyRelationFormat(BaseException):

    def __init__(self, expression, *args) -> None:
        super().__init__(f'Invalid relation format in {expression}', *args)
        return
    pass

class LocalFieldIsDescriptor(BaseException):

    def __init__(self, name:str, model_name: str, *args) -> None:
        super().__init__('Bad configuration, '\
            '%s is a descriptor in model %s'\
            %(name, model_name), *args)
        return
    pass

class FieldIsPrivated(BaseException):

    def __init__(self, field_name: str, *args) -> None:
        super().__init__('The requested field \'%s\' is privated'%field_name, *args)
        return
    pass

class ObjectToRelateDoesNotExists(BaseException):

    def __init__(self, relation_field_name:str, objected_pk:str, *args) -> None:
        super().__init__(
            'Doesn\'t exists the identified %s with %s'%(relation_field_name, objected_pk),
            *args
        )
