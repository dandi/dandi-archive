from pathlib import Path

from setuptools import find_packages, setup

import versioneer

readme_file = Path(__file__).parent / 'README.md'
if readme_file.exists():
    with readme_file.open() as f:
        long_description = f.read()
else:
    # When this is first installed in development Docker, README.md is not available
    long_description = ''

setup(
    name='dandiapi',
    version=versioneer.get_version(),
    description='',
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
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python',
    ],
    python_requires='>=3.8',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'celery',
        'dandischema==0.5.2',
        # TODO: Remove this. Pinning Django to 3.x until
        # https://github.com/jazzband/django-oauth-toolkit/issues/1037 is resolved
        'django~=3.2',
        'django-admin-display',
        'django-allauth',
        'django-click',
        'django-configurations[database,email]',
        'django-extensions',
        'django-filter',
        'django-guardian',
        'django-oauth-toolkit',
        'djangorestframework',
        'djangorestframework-yaml',
        'drf-extensions',
        'drf-yasg',
        'httpx',
        'jsonschema',
        'pydantic',
        'boto3[s3]',
        # Production-only
        'django-composed-configuration[prod]>=0.19.2',
        'django-s3-file-field[boto3]==0.1.1',
        'django-storages[boto3]',
        'gunicorn',
        # Development-only, but required
        'django-minio-storage',
        # Temporary dependency for user migration
        'versioneer',
    ],
    extras_require={
        'dev': [
            'django-composed-configuration[dev]>=0.19.2',
            'django-debug-toolbar',
            'django-s3-file-field[minio]',
            'ipython',
            'tox',
            'boto3-stubs[s3]',
        ],
        'test': [
            'factory-boy',
            'pytest',
            'pytest-cov',
            'pytest-django',
            'pytest-factoryboy',
            'pytest-mock',
            'requests',
        ],
    },
    cmdclass=versioneer.get_cmdclass(),
)
