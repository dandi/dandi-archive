FROM girder/girder:latest-py3

WORKDIR /home

COPY docker/provision provision

COPY girder-dandi-archive /home/girder-dandi-archive

RUN pip install -e /home/girder-dandi-archive && girder build

ENTRYPOINT ["/home/provision/girder_entrypoint.sh"]