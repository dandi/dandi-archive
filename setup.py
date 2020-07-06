from setuptools import setup

with open('README.md') as readme_file:
    readme = readme_file.read()

requirements = [
    'boto3',
    'celery',
    'dandi',
    'dj-database-url',
    'django',
    'django-admin-display',
    'django-configurations',
    'django-cors-headers',
    'django-debug-toolbar',
    'django-extensions',
    'django-filter',
    'django-minio-storage',
    'django-storages',
    'djangorestframework',
    'drf-extensions',
    'drf-yasg',
    'httpx',
    'psycopg2',
    'pyyaml',
    'whitenoise',
]

setup(
    python_requires='>=3.8.0',
    install_requires=requirements,
    license='Apache Software License 2.0',
    long_description=readme,
    long_description_content_type='text/x-md',
    name='dandi_publish',
    version='0.1.0',
)
