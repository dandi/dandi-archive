from django.core import signing
from django.http.response import HttpResponseBase
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    parser_classes,
    permission_classes,
)
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from s3_file_field.fields import S3FileField
from s3_file_field._multipart import MultipartManager, PartFinalization, UploadFinalization

from dandiapi.api.models import Validation
from dandiapi.api.tasks import validate
from dandiapi.api.views.serializers import ValidationSerializer


class UploadInitializationRequestSerializer(serializers.Serializer):
    file_name = serializers.CharField(trim_whitespace=False)
    file_size = serializers.IntegerField(min_value=1)
    sha256 = serializers.CharField(trim_whitespace=False)
    # part_size = serializers.IntegerField(min_value=1)


class PartInitializationResponseSerializer(serializers.Serializer):
    part_number = serializers.IntegerField(min_value=1)
    size = serializers.IntegerField(min_value=1)
    upload_url = serializers.URLField()


class UploadInitializationResponseSerializer(serializers.Serializer):
    object_key = serializers.CharField(trim_whitespace=False)
    upload_id = serializers.CharField()
    parts = PartInitializationResponseSerializer(many=True, allow_empty=False)


class ObjectAlreadyExistsResponseSerializer(serializers.Serializer):
    message = serializers.CharField(default="Object with that checksum already exists")
    object_key = serializers.CharField(trim_whitespace=False)


class PartCompletionRequestSerializer(serializers.Serializer):
    part_number = serializers.IntegerField(min_value=1)
    size = serializers.IntegerField(min_value=1)
    etag = serializers.CharField()

    def create(self, validated_data) -> PartFinalization:
        return PartFinalization(**validated_data)


class UploadCompletionRequestSerializer(serializers.Serializer):
    field_id = serializers.CharField()
    object_key = serializers.CharField(trim_whitespace=False)
    upload_id = serializers.CharField()
    parts = PartCompletionRequestSerializer(many=True, allow_empty=False)

    def create(self, validated_data) -> UploadFinalization:
        parts = [
            PartFinalization(**part)
            for part in sorted(validated_data.pop('parts'), key=lambda part: part['part_number'])
        ]
        del validated_data['field_id']
        return UploadFinalization(parts=parts, **validated_data)


class UploadCompletionResponseSerializer(serializers.Serializer):
    complete_url = serializers.URLField()
    body = serializers.CharField(trim_whitespace=False)


class UploadValidationRequestSerializer(serializers.Serializer):
    object_key = serializers.CharField(trim_whitespace=False)
    sha256 = serializers.CharField(trim_whitespace=False)

    def create(self, validated_data) -> Validation:
        return Validation(
            blob=validated_data['object_key'],
            sha256=validated_data['sha256'],
            state=Validation.State.IN_PROGRESS,
        )


class UploadValidationResponseSerializer(serializers.Serializer):
    pass


@swagger_auto_schema(method='POST', request_body=UploadInitializationRequestSerializer())
@api_view(['POST'])
@parser_classes([JSONParser])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def upload_initialize_view(request: Request) -> HttpResponseBase:
    request_serializer = UploadInitializationRequestSerializer(data=request.data)
    request_serializer.is_valid(raise_exception=True)
    upload_request: Dict = request_serializer.validated_data
    try:
        validation: Validation = Validation.objects.get(sha256=upload_request['sha256'])
        if validation.object_key_exists():
            response_serializer = ObjectAlreadyExistsResponseSerializer(
                {'object_key': validation.blob.name}
            )
            return Response(response_serializer.data)
        # If there is a validation, but no object in the object store, proceed with upload
    except Validation.DoesNotExist:
        # Proceed with the upload
        pass

    # TODO The first argument to generate_filename() is an instance of the model.
    # We do not and will never have an instance of the model during field upload.
    # Maybe we need a different generate method/upload_to with a different signature?
    object_key = Validation.blob.field.storage.generate_filename(upload_request['file_name'])

    initialization = MultipartManager.from_storage(Validation.blob.field.storage).initialize_upload(
        object_key, upload_request['file_size']
    )

    response_serializer = UploadInitializationResponseSerializer(initialization)
    return Response(response_serializer.data)


@swagger_auto_schema(method='POST', request_body=UploadCompletionRequestSerializer())
@api_view(['POST'])
@parser_classes([JSONParser])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def upload_complete_view(request: Request) -> HttpResponseBase:
    request_serializer = UploadCompletionRequestSerializer(data=request.data)
    request_serializer.is_valid(raise_exception=True)
    completion: UploadCompletion = request_serializer.save()

    completed_upload = MultipartManager.from_storage(Validation.blob.field.storage).complete_upload(
        completion
    )

    # TODO: what is the response?
    response_serializer = UploadCompletionResponseSerializer(
        {
            'complete_url': completed_upload.complete_url,
            'body': completed_upload.body,
        }
    )
    return Response(response_serializer.data)


@swagger_auto_schema(method='POST', request_body=UploadValidationRequestSerializer())
@api_view(['POST'])
@parser_classes([JSONParser])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def upload_validate_view(request: Request) -> HttpResponseBase:
    request_serializer = UploadValidationRequestSerializer(data=request.data)
    request_serializer.is_valid(raise_exception=True)
    validation: Validation = request_serializer.save()

    # Use the validation from the DB if it already exists
    try:
        validation = Validation.objects.get(sha256=validation.sha256)
        if validation.state == Validation.State.IN_PROGRESS:
            raise ValidationError('Validation already in progress')
        validation.state = Validation.State.IN_PROGRESS
    except Validation.DoesNotExist:
        pass

    if not validation.object_key_exists():
        raise ValidationError('Object does not exist')

    validation.save()

    validate.delay(validation.id)
    return Response(status=status.HTTP_204_NO_CONTENT)


@swagger_auto_schema(method='GET')
@api_view(['GET'])
@parser_classes([JSONParser])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def upload_get_validation_view(request: Request, sha256: str) -> HttpResponseBase:
    # request_serializer = UploadValidationRequestSerializer(data=request.data)
    # request_serializer.is_valid(raise_exception=True)
    validation = get_object_or_404(Validation, sha256=sha256)

    response_serializer = ValidationSerializer(validation)
    return Response(response_serializer.data)
