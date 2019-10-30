FROM python:3.7

RUN pip install girder-client

WORKDIR /home

COPY docker/provision provision

ENTRYPOINT ["/home/provision/provision_entrypoint.sh"]