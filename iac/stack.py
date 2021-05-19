import os

from aws_cdk import (
    core as cdk,
    aws_efs as efs,
    aws_ec2 as ec2,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions
)


class EfsBackupDemoStack(cdk.Stack):
    VPC_ID = os.environ['VPC_ID']
    NOTIFICATION_EMAIL = os.environ['NOTIFICATION_EMAIL']

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # import existing infrastructure
        vpc = ec2.Vpc.from_lookup(
            self, 'Vpc',
            vpc_id=self.VPC_ID
        )

        # create EFS security group with generous rules
        file_system_sg = ec2.SecurityGroup(
            self, 'EfsSecurityGroup',
            vpc=vpc,
            allow_all_outbound=True
        )

        file_system_sg.add_ingress_rule(
            self,
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(2049),
            description='efs-dev access'
        )

        file_system_sg.apply_removal_policy(cdk.RemovalPolicy.DESTROY)

        # create EFS for sharing with ec2
        file_system = efs.FileSystem(
            self, 'EfsFileSystem',
            vpc=vpc,
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            security_group=file_system_sg,
            removal_policy=cdk.RemovalPolicy.DESTROY  # demo purposes only
        )

        # create SNS topic and subscription for notifications
        topic = sns.Topic(
            self, 'EFSandGlacierJobs',
            display_name='EFS and Glacier job notification topic',
            topic_name='EfsAndGlacierTopic'
        )

        topic.add_subscription(
            self,
            subscriptions.EmailSubscription(self.NOTIFICATION_EMAIL, json=True)
        )

        topic.apply_removal_policy(cdk.RemovalPolicy.DESTROY)

        # create s3 glacier vault and post to SNS topic

        # create lambda -> start ec2 instance
