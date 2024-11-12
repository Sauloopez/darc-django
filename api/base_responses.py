from django.http.response import JsonResponse

permission_denied_response = JsonResponse(
    {'message': 'You do not have permission for access here'},
    status=403
    )

login_required_response = JsonResponse(
    {'message': 'You are not authenticated'},
    status=401
    )

must_be_json_response = JsonResponse(
    {'message': 'Content type must be application/json'},
    status=400
)

no_request_body_response = JsonResponse(
    {'message': 'The request has not valid body'},
    status=400
)

missing_fields_response = lambda fields: JsonResponse(
    {'message': f'Some of the fields: {fields} are missing in request'},
    status=400
)

invalid_fields_response = lambda fields: JsonResponse(
    {'message': f'Some of the fields: {fields} can\'t be found'},
    status=400
)

__all__= [
    'permission_denied_response',
    'login_required_response',
    'must_be_json_response',
    'no_request_body_response',
    'missing_fields_response'
]
