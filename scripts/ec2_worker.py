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
BUCKET_NAME = os.environ['BUCKET_NAME']  # throw error if not set
GLACIER_RETRIEVAL_TIER = 'Expedited'  # available in 1 -5 minutes; default is Standard

# configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')

# configure boto session
session = boto3.Session(profile_name=WORKER_PROFILE)

# configure services being used for operation
s3 = session.client('s3')
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


# upload to files to s3 glacier
def upload_s3_glacier(items: list[str]) -> None:
    for item in items:
        head, tail = os.path.split(item)  # get path and filename
        file_stream = create_file_stream(item)  # convert to binary
        try:
            logging.info(f'Uploading {item} to {BUCKET_NAME} ...')
            s3.upload_fileobj(file_stream, BUCKET_NAME, tail)
        except ClientError as e:
            logging.error(e)
            exit()
        finally:
            file_stream.close()


# execute upload to s3 glacier and kickoff job for inventory-retrieval
upload_s3_glacier(source_files)
