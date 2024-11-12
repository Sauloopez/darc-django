
# Django Auto REST CRUD

>[!IMPORTANT]
> DARC is solely async.

>[!IMPORTANT]
> Is full JSON.

## Feature
---
The principal feature of this class is allows inherits of another CBV (Class Based Views).
Too, ease the CRUD creation with REST interface in Django models. Although DRF(Django REST Framework) exists,
this no supports asynchronus operations, and is so big and a bit complex. BASE API REST simplify all without serializers,
just arrays and dicts.<br>

The principal idea, is just it:
```python
class SomeClassView(BaseRESTView):
    model = MyModel
    fields = {
        'field1',
        'field2',
        ('some_relation': ['relation_field_A', 'relation_field_B']),
    }
```

## Getting Started

So, in `models.py` into a django app, are the models `Team` and `Player`.

```python
from django.db import models

class Team(models.Model):
    name= models.CharField(max_length=50)
    pass

class Player(models.Model):
    first_name= models.CharField(max_length=50)
    last_name= models.CharField(max_length=50)
    team= models.ForeignKey(Team, related_name= 'players')
    pass
```

Now into `views.py`, create the async REST API views with inherits.

```python
from api.base_api import BaseRESTView
from .models import Team, Player

class TeamREST(BaseRESTView):
    model= Team
    fields= {
        'id',
        'name',
        ('players', ['id', 'first_name', 'last_name'])
    }
    pass

class PlayerREST(BaseRESTView):
    model= Player
    fields= {
        'id',
        'first_name',
        'last_name',
        ('team', ['id', 'name'])
    }
```

Finally, in `urls.py` file of your django project, add your ready REST API views.

```python
# import the TeamREST and PlayerREST views before
from django.urls import path, re_path

urlpatterns = [
    re_path(r'^teams(?:(/(?P<id>\d+))?)/$', TeamREST.as_view()),
    re_path(r'^players(?:(/(?P<id>\d+))?)/$', PlayerREST.as_view()),
]
```
And run the django project with a asynchronus server (ASGI).


## Class Variables
### **model**
Is the Django model for make CRUD, can't be abstract.
### **allow_only_fields**
On `True`, it allows parse fields finded in `onlyFields` request URL params in GET method.
### **allow_pagination**
On `True`, allows the pagination in GET method. Takes `pages` and/or `itemsPerPage` in request URL params
### **fields**
The sintaxis that express the model fields for parse a model instance to a possible dict serializable for a JsonResponse.<br>

**Composition:**<br>

A clear expression for this fields, is simple. To difference at DRF, doesn't necesary a field parsing, or a serializer.
This variable can be expressed by a set or a string with '\___all___' expression. In the set, each model field that wants display, its name should be added to this set.<br>

**Example:**<br>

```python
#models.py
from django.db import models

class Book(models.Model):
    name= models.CharField(max_length=50)
    isbn= models.CharField(max_length=20)
    pass

#views.py
from api.base_api import BaseRESTView
from .models import Book

class BookView(BaseRESTView):
    model= Book
    # Just some fields...
    fields= {'name', 'isbn'}
    # or can be '__all__':
    fields= '__all__'
    pass
```

Is possible too express a relation. For it, add a tuple into the `fields`, where
the first value is the relation field, the second  value must be a tuple or a list
with the relation's fields. For example:

```python
#models.py
from django.db import models

class Author(models.Model):
    first_name= models.CharField(max_length=50)
    last_name= models.CharField(max_length=50)
    pass

class Book(models.Model):
    name= models.CharField(max_length=50)
    isbn= models.CharField(max_length=20)
    author= models.ForeignKey(Author, related_name='books')
    pass


#views.py
from api.base_api import BaseRESTView
from .models import Author, Book

class BookView(BaseRESTView):
    model= Book
    fields= {
        'name',
        ('author', ['first_name'])
    }
    pass

class AuthorView(BaseRESTView):
    model= Author
    fields= {
        'first_name',
        ('books', ['name', 'isbn'])
    }
```

## GET Method Features:

This provides some features for the GET HTTP method, same:

### Pagination:

For make the include the in a request GET HTTP, must be exixts the number of pages or the items per page as GET URL keys, e.g.

```
/my/view/path/?pages=1
```
or
```
/my/view/path/?itemsPerPage=10
```
or
```
/my/view/path/?pages=1&itemsPerPage=10
```

### Retrieve especified fields

This feature allows retrieve especific fields for a model, for example, if want retireve just the `id` for a model, is possible so:
```
/my/view/path/?onlyFields=id
```
Is possible too especify more than one fields...
```
/my/view/path/?onlyFields=id,name
```
And especify too, the fields of the relations, example:
```
/my/view/path/?onlyFields=id,name,author.first_name,author.id
```
Or, if want retrieve all fields, is possible too, just...
```
/my/view/path/?onlyFields=__all__
```
Just retrieve the name of **model fields** retrieved on:
```python
MyModel._meta.fields
# so, the names  are:
[field.name for field in MyModel._meta.fields]
```
