import os
import sys
import argparse
import boto3
import requests
import shutil

os.environ['AWS_ACCESS_KEY_ID'] = 'admin'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'miniopassword'

# Django
PUBLISH_API_URL = 'http://localhost:8000/api/dandisets/'
# Minio
S3_URL = 'http://localhost:9000'
# For local downloading
FILE_ROOT = '/tmp/'


def download(s3, path):
    # path is both an s3 path and a file path
    print(f'Downloading {path}')
    s3_response = s3.get_object(Bucket='dandi', Key=path)
    body = s3_response['Body'].read()

    with open(FILE_ROOT + path, 'wb') as f:
        f.write(body)


parser = argparse.ArgumentParser(
    description='Demo downloading a published dandiset')
parser.add_argument('identifier', type=str, help='dandiset identifier')
parser.add_argument('-v', '--version', type=int, default=None,
                    help='dandiset version')

if __name__ == '__main__':
    args = parser.parse_args()

    identifier = args.identifier
    version = args.version

    if not args.version:
        print('No version specified, looking up most recent version')
        response = requests.get(PUBLISH_API_URL + args.identifier)
        if response.status_code == 404:
            print(f'Published dandiset {identifier} not found')
            sys.exit(1)
        version = response.json()['version']
        print(f'Found version {version}')
    response = requests.get(
        PUBLISH_API_URL + identifier + '/' + str(version))
    if response.status_code == 404:
        print(f'Published dandiset {identifier}/{version} not found')
        sys.exit(1)

    dandiset_path = 'dandisets/' + identifier + '/' + str(version)

    # Delete and recreate local download location
    shutil.rmtree(FILE_ROOT + dandiset_path, ignore_errors=True)
    os.makedirs(FILE_ROOT + dandiset_path)

    # Set up S3 client
    s3 = boto3.client('s3', endpoint_url=S3_URL)

    download(s3, dandiset_path + '/dandiset.yaml')

    dandiset = response.json()
    subjects = dandiset['subjects']
    for subject in subjects:
        subject_path = dandiset_path + '/' + subject['name']
        os.makedirs(FILE_ROOT + subject_path)
        nwb_files = subject['nwb_files']
        for nwb_file in nwb_files:
            nwb_file_path = subject_path + '/' + nwb_file['name']
            download(s3, nwb_file_path)
