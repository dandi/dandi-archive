#!/usr/bin/env python3
"""Script that will export all desired papertrail log files."""
from datetime import datetime
import os
from pathlib import Path

import click
from click.exceptions import ClickException
import requests
from tqdm import tqdm

PAPERTRAIL_TOKEN = os.getenv('PAPERTRAIL_APIKEY', None)


@click.command()
@click.option(
    '--start', help='The UTC datetime string to determine the beginning of logs', default=None
)
@click.option('--end', help='The UTC datetime string to determine the end of logs', default=None)
@click.option(
    '-f',
    '--force',
    'force',
    is_flag=True,
    help='Force overwrite any existing log files',
    default=False,
)
@click.option(
    '-a', '--amend', 'amend', is_flag=True, help='Amend any existing log files', default=False
)
@click.option(
    '-o', '--out', 'output_file', help='The output file', default='logs.tsv.gz', show_default=True
)
def cli(start, end, force, amend, output_file):
    if PAPERTRAIL_TOKEN is None:
        raise ClickException(
            'Must set the PAPERTRAIL_APIKEY environment variable. '
            'You can find this at https://papertrailapp.com/account/profile '
            '(must be logged in with heroku).'
        )

    if force and amend:
        raise ClickException('Must choose only one of force or amend flags.')

    # Check existing output file
    output_file = Path(output_file)
    if output_file.exists():
        if not (force or amend):
            raise ClickException(
                f'Output file {output_file} already exists.'
                ' Please specify one of --force or --amend.'
            )

        # Remove
        if force:
            output_file.unlink()

    # Get archive list
    headers = {'X-Papertrail-Token': PAPERTRAIL_TOKEN}
    resp = requests.get(
        'https://papertrailapp.com/api/v1/archives.json', headers=headers, timeout=30
    )
    if not resp.ok:
        raise ClickException('Could not retrieve archive list')
    archives: list[dict] = resp.json()

    # Find most recent archive entry
    last_log_entry = 0
    if end:
        fixed_end = datetime.fromisoformat(end).isoformat()
        last_log_entry = next(
            (i for i, x in enumerate(archives) if x['start'].rstrip('Z') == fixed_end), None
        )
        if last_log_entry is None:
            raise ClickException(f'Could not find matching archive entry for end datetime: {end}')

    # Find oldest archive entry
    first_log_entry = len(archives) - 1
    if start:
        fixed_start = datetime.fromisoformat(start).isoformat()
        first_log_entry = next(
            (i for i, x in enumerate(archives) if x['start'].rstrip('Z') == fixed_start), None
        )
        if first_log_entry is None:
            raise ClickException(
                f'Could not find matching archive entry for start datetime: {start}'
            )

    # Ensure output file exists
    if not output_file.exists():
        output_file.touch()

    # Function to download an archive
    def download_archive(archive: dict):
        link = archive['_links']['download']['href']
        resp = requests.get(link, headers=headers, timeout=30, stream=True)
        with output_file.open('ab') as outfile:
            outfile.write(resp.raw.read())

    # Iterate over every entry within range
    start_time = archives[first_log_entry]['start'].rstrip('Z')
    end_time = archives[last_log_entry]['end'].rstrip('Z')
    click.echo(
        f'Beginning download of {first_log_entry + 1 - last_log_entry} hourly log archives'
        f' between {start_time} and {end_time}'
    )
    for i in tqdm(range(first_log_entry, last_log_entry - 1, -1)):
        download_archive(archives[i])


if __name__ == '__main__':
    cli()
