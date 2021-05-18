import os
import logging
import boto3
import pathlib
import re
from typing import BinaryIO
from botocore.exceptions import ClientError

# set variables
WORKER_PROFILE = os.getenv('WORKER_AWS_PROFILE', 'default')  # optional; defaults to iam role
VAULT = os.environ['VAULT']  # throw error if not set
SOURCE_DIR = os.environ['SOURCE_DIR']  # throw error if not set
GLACIER_RETRIEVAL_TIER = 'Expedited'  # available in 1 -5 minutes; default is Standard

# configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')

# configure boto session
session = boto3.Session(profile_name=WORKER_PROFILE)

# configure services being used for operation
glacier = session.client('glacier')
sns = session.client('sns')

# get directory where files are stored
source_folder = pathlib.Path(SOURCE_DIR)

# list files in directory and store for glacier iteration; ignore hidden files
source_files = []
hidden_pattern = '^\\..+'
for root, directories, files in os.walk(source_folder, topdown=False):
    for name in files:
        if re.match(hidden_pattern, name):
            continue
        filePath = os.path.join(root, name)
        if os.stat(filePath).st_size > 0:
            source_files.append(filePath)


# convert files to streams
def create_file_stream(source_file: str) -> BinaryIO:
    try:
        object_data = open(source_file, 'rb')  # need to close this later
        return object_data
    except Exception as e:
        logging.error(e)
        exit()


# upload to files  to glacier
def upload_s3_glacier(items: list[str]) -> list:
    archive_result = []
    for item in items:
        file_stream = create_file_stream(item)
        try:
            logging.info(f'Uploading {item} to {VAULT} ...')
            archive_response = glacier.upload_archive(vaultName=VAULT, body=file_stream)
            archive_result.append(archive_response)
        except ClientError as e:
            logging.error(e)
            exit()
        finally:
            file_stream.close()
    return archive_result


# execute upload to s3 glacier and kickoff job for inventory-retrieval
archives = upload_s3_glacier(source_files)
if len(archives) != 0:
    job = glacier.initiate_job(vaultName=VAULT, jobParameters={
        'Type': 'inventory-retrieval',
        'Tier': GLACIER_RETRIEVAL_TIER
    })
    for archive in archives:
        logging.info(f'Archive {archive["archiveId"]} added to {VAULT}')
    logging.info(f'Inventory started and can be queried at {job["jobId"]}')
else:
    logging.info('No archives uploaded')
