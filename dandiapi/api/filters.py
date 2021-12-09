from django.contrib.auth.models import User
import django_filters


class UserStatusFilter(django_filters.FilterSet):
    class Meta:
        model = User
        fields = ['metadata__status']
