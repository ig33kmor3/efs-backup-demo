import json
import os
import boto3


def handler(event, context):
    # import from environment variables
    instance_id = os.environ['INSTANCE_ID']

    # set environment variables
    ec2 = boto3.resource('ec2')
    instance = ec2.Instance(instance_id)

    # start ec2 worker to execute backups
    instance.start()

    # return a response
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "status": "successful"
        })
    }
