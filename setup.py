from pathlib import Path

from setuptools import find_namespace_packages, setup

readme_file = Path(__file__).parent / 'README.md'
if readme_file.exists():
    with readme_file.open() as f:
        long_description = f.read()
else:
    # When this is first installed in development Docker, README.md is not available
    long_description = ''

setup(
    name='dandiapi',
    description='',
    # Determine version with scm
    use_scm_version={'version_scheme': 'post-release'},
    setup_requires=['setuptools_scm'],
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='Apache 2.0',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    keywords='',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django :: 3.0',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python',
    ],
    python_requires='>=3.11',
    packages=find_namespace_packages(include=['dandiapi*']),
    include_package_data=True,
    install_requires=[
        'celery',
        'dandischema~=0.8.4',
        'django~=4.1.0',
        'django-admin-display',
        'django-allauth',
        'django-click',
        'django-configurations[database,email]',
        'django-extensions',
        'django-filter',
        'django-guardian',
        'django-oauth-toolkit>=1.7,<2',
        'djangorestframework',
        'djangorestframework-yaml',
        'drf-extensions',
        'drf-yasg',
        'jsonschema',
        'pydantic',
        'boto3[s3]',
        'more_itertools',
        'requests',
        's3-log-parse',
        'zarr-checksum>=0.2.8',
        # Production-only
        'django-composed-configuration[prod]>=0.23.0',
        # pin directly to a version since we're extending the private multipart interface
        'django-s3-file-field[boto3]==0.3.2',
        'django-storages[s3]>=1.14.2',
        'gunicorn',
        # Development-only, but required
        # TODO: starting with v0.5.0, django-minio-storage requires v7
        # of the minio-py library. minio-py 7 introduces several
        # breaking changes to the API, and django-s3-file-field is also
        # incompatible with it since it has minio<7 as a dependency.
        # Until these issues are resolved, we pin it to an older version.
        'django-minio-storage<0.5.0',
        'tqdm',
    ],
    extras_require={
        'dev': [
            'django-composed-configuration[dev]>=0.23.0',
            'django-debug-toolbar',
            'django-s3-file-field[minio]',
            'ipython',
            'tox',
            'memray',
            'boto3-stubs[s3]',
            'django-stubs',
            'djangorestframework-stubs',
            'types-setuptools',
        ],
        'test': [
            'factory-boy',
            'freezegun',
            'pytest',
            'pytest-cov',
            'pytest-django',
            'pytest-factoryboy',
            'pytest-memray',
            'pytest-mock',
        ],
    },
)
