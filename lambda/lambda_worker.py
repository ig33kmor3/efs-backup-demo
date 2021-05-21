import json
import os
import boto3


def handler(event, context):
    # import from environment variables
    instance_id = os.environ['INSTANCE_ID']

    # set variables
    ec2 = boto3.resource('ec2')
    instance = ec2.Instance(instance_id)
    commands = json.load(event.body)

    # start ec2 worker to execute backups
    try:
        if commands['isStart']:
            instance.start()
            print(f'Successfully started {instance_id}!')
        else:
            instance.stop()
            print(f'Successfully stopped {instance_id}!')
    except Exception as e:
        print(e)
        # return Failure response
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'status': 'Failure'
            })
        }

    # return Success response
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'status': 'Success'
        })
    }
