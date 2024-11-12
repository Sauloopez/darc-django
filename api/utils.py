from django.http import HttpRequest
from functools import wraps
import json
from . import base_responses

def get_model_fields(model):
    return {field.name for field in model._meta.fields}

def get_required_model_fields(model) -> set[str]:
    return {field.name for field in model._meta.fields if field.blank == False}

def validate_json_request_body(view_func):
    @wraps(view_func)
    async def wrapper(*args, **kwargs):
        req = args[1]
        if isinstance(req, HttpRequest):
            if not req.headers.get('Content-Type') == 'application/json':
                return base_responses.must_be_json_response
            if not req.body:
                return base_responses.no_request_body_response
            try:
                json_data = json.loads(req.body)
                setattr(req, 'json_data', json_data)
            except json.JSONDecodeError:
                return base_responses.no_request_body_response
        return await view_func(*args, **kwargs)
    return wrapper

def validate_data_fields(fields : set[str]|None = None):
    def decorator(view_func):
        @wraps(view_func)
        async def wrapper(*args, **kwargs):
            req = args[1]
            view = args[0]
            if isinstance(req, HttpRequest):
                if not getattr(req, 'json_data', None):
                    return base_responses.no_request_body_response
                _fields: set[str] = fields or getattr(view, 'required_model_fields', set())
                if not _fields:
                    raise Exception('Invalid fields configuration')
                for field in _fields:
                    try:
                        req.json_data[field]
                    except KeyError:
                        return base_responses.missing_fields_response(_fields)
            return await view_func(*args, **kwargs)
        return wrapper
    return decorator

def validate_updatable_fields(fields : set[str]|None = None):
    def decorator(view_func):
        @wraps(view_func)
        async def wrapper(*args, **kwargs):
            req = args[1]
            view = args[0]
            if isinstance(req, HttpRequest):
                if not getattr(req, 'json_data', None):
                    return base_responses.no_request_body_response
                _fields: set[str] = fields or getattr(view, 'required_model_fields', set())
                _fields-= getattr(view, 'nonupdatable_fields', set())
                if not _fields:
                    raise Exception('Invalid fields configuration')
                for field in _fields:
                    try:
                        req.json_data[field]
                    except KeyError:
                        return base_responses.missing_fields_response(_fields)
            return await view_func(*args, **kwargs)
        return wrapper
    return decorator

def parse_possible_json_data(view_func):
    async def wrapper(*args, **kwargs):
        if isinstance(args[1], HttpRequest):
            if args[1].headers.get('Content-Type') == 'application/json':
                if args[1].body:
                    setattr(args[1], 'json_data', json.loads(args[1].body))
            return await view_func(*args, **kwargs)
    return wrapper

def validate_possible_json_keys(possible_keys : list[str]):
    def decorator(view_func):
        @wraps(view_func)
        async def wrapper(*args, **kwargs):
            if json_data:=getattr(args[1], 'json_data', None):
                keys = json_data.keys()
                for key in possible_keys:
                    if key not in keys:
                        return base_responses.missing_fields_response(possible_keys)
            return await view_func(*args, **kwargs)
        return wrapper
    return decorator

def validate_optional_fields(fields : list):
    def decorator(view_func):
        @wraps(view_func)
        async def wrapper(*args, **kwargs):
            req = args[1]
            if isinstance(req, HttpRequest):
                if not getattr(req, 'json_data', None):
                    return base_responses.no_request_body_response
                for key in req.json_data.keys():
                    if key not in fields:
                        req.json_data.pop(key)
            return await view_func(*args, **kwargs)
        return wrapper
    return decorator
