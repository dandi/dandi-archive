import djclick as click

from dandiapi.api.models import Version

# maps name of metadata field to its correct value for "schemaKey"
SCHEMA_KEYS = {
    '': 'Dandiset',
    'access': 'AccessRequirements',
    'relatedResource': 'Resource',
    'assetsSummary': 'AssetsSummary',
}


@click.command()
def repair_schema_keys():
    versions = Version.objects.filter(validation_errors__isnull=False)
    for version in versions:
        for error in version.validation_errors:
            if "'schemaKey' is a required property" in error['message']:
                error_split: list[str] = error['field'].split('.')
                field = error_split[0]

                if field == '':
                    version.metadata['schemaKey'] = SCHEMA_KEYS[field]
                elif len(error_split) == 1:
                    version.metadata[field]['schemaKey'] = SCHEMA_KEYS[field]
                else:
                    # handles cases where error is like "relatedResource.0"
                    index = int(error_split[1])
                    version.metadata[field][index]['schemaKey'] = SCHEMA_KEYS[field]
                version.save()
