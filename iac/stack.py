import os

from aws_cdk import (
    core as cdk,
    aws_efs as efs,
    aws_ec2 as ec2
)


class EfsBackupDemoStack(cdk.Stack):
    VPC_ID = os.environ['VPC_ID']

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # import existing infrastructure
        vpc = ec2.Vpc.from_lookup(
            self, 'Vpc',
            vpc_id=self.VPC_ID
        )

        # create EFS for sharing with ec2
        filesystem = efs.FileSystem(
            self, 'EfsFileSystem',
            vpc=vpc,
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            removal_policy=cdk.RemovalPolicy.DESTROY  # demo purposes only
        )

        # create lambda -> start ec2 instance

        # create SNS topic for notifications

        # create s3 glacier vault and post to SNS topic
