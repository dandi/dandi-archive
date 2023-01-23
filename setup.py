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
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python',
    ],
    python_requires='>=3.10',
    packages=find_namespace_packages(include=['dandiapi*']),
    include_package_data=True,
    install_requires=[
        'celery',
        'dandischema~=0.7.1',
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
        # Production-only
        'django-composed-configuration[prod]>=0.22.0',
        # pin directly to a version since we're extending the private multipart interface
        'django-s3-file-field[boto3]==0.3.2',
        'django-storages[boto3]',
        'gunicorn',
        # Development-only, but required
        'django-minio-storage',
        'tqdm',
    ],
    extras_require={
        'dev': [
            'django-composed-configuration[dev]>=0.22.0',
            'django-debug-toolbar',
            'django-s3-file-field[minio]',
            'ipython',
            'tox',
            'memray',
        ],
        'test': [
            'factory-boy',
            'pytest',
            'pytest-cov',
            'pytest-django',
            'pytest-factoryboy',
            'pytest-memray',
            'pytest-mock',
        ],
        'lint': [
            'flake8==6.0.0',
            'flake8-black==0.3.6',
            'flake8-bugbear==23.1.20',
            'flake8-docstrings==1.6.0',
            'flake8-isort==6.0.0',
            'flake8-quotes==3.3.2',
            'pep8-naming==0.13.3',
        ],
        'type': [
            'mypy==0.991',
            'boto3-stubs[s3]==1.26.50',
            'django-stubs==1.13.1',
            'djangorestframework-stubs==1.8.0',
            'types-setuptools==65.7.0.1',
        ],
    },
)
