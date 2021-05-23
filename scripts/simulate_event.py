import json
import os
import boto3
import logging

# set variables
WORKER_PROFILE = os.environ['WORKER_AWS_PROFILE']  # throw error if not set
LAMBDA_TOPIC_ARN = os.environ['LAMBDA_TOPIC_ARN']  # throw error if not set

# configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')

# configure boto session for either ec2 role or local profile
session = boto3.Session(profile_name=WORKER_PROFILE)

# configure services being used for operation
sns = session.client('sns')


# publish to sns and invoke lambda
def notify_lambda(is_start: bool) -> None:
    message = json.dumps({
        'isStart': is_start
    })

    sns.publish(
        TopicArn=LAMBDA_TOPIC_ARN,
        Message=message
    )


# execute manual trigger of lambda notification
notify_lambda(is_start=True)
logging.info('Notified Lambda Worker to boot EC2 Instance for EFS backup to S3 Glacier!')
