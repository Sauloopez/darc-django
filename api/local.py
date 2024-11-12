from django.db.models import Model, Field
from api import exceptions

class LocalField:

    def __init__(self, name: str, model: type[Model]) -> None:
        self._name = name
        self._model = model
        try:
            self._deferred_atribute = getattr(model, name)
            self._model_field :Field = self._deferred_atribute.field
        except AttributeError:
            raise exceptions.FieldNotInModel(name, model._meta.model_name)
        if (
            getattr(self._model_field, 'rel', None) or
            getattr(self._model_field, 'related', None) or
            getattr(self._model_field, 'is_relation', None)
        ):
            raise exceptions.LocalFieldIsDescriptor(name, model._meta.model_name)
        return

    @property
    def name(self):
        return self._name

    @property
    def model(self):
        return self._model

    @property
    def model_field(self):
        return self._model_field

    def __repr__(self) -> str:
        return self._name
    pass
