from setuptools import setup, find_packages

with open("README.rst") as readme_file:
    readme = readme_file.read()

requirements = [
    "girder>=3.0.0a1",
    "girder-download-statistics",
    "girder-homepage",
    "girder-oauth",
    "girder-sentry",
]

setup(
    author="michael grauer",
    author_email="michael.grauer@kitware.com",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    description="A Girder plugin used as a prototype DANDI neuroscience archive.",
    install_requires=requirements,
    license="Apache Software License 2.0",
    long_description=readme,
    long_description_content_type="text/x-rst",
    include_package_data=True,
    keywords="girder-plugin, dandi_archive",
    name="girder_dandi_archive",
    packages=find_packages(exclude=["test", "test.*"]),
    url="https://github.com/dandi/dandiarchive",
    version="0.1.0",
    zip_safe=False,
    entry_points={
        "girder.plugin": ["dandi_archive = girder_dandi_archive:GirderPlugin"]
    },
)
