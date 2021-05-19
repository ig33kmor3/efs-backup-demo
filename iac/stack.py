import os

from aws_cdk import (
    core as cdk,
    aws_efs as efs,
    aws_ec2 as ec2,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions
)
from aws_cdk.core import Stack


class EfsBackupDemoStack(cdk.Stack):
    VPC_ID = os.environ['VPC_ID']  # throw error if not set
    NOTIFICATION_EMAIL = os.environ['NOTIFICATION_EMAIL']  # throw error if not set
    KEY_PAIR_NAME = os.environ['KEY_PAIR_NAME']  # throw error if not set
    REGION = os.environ['REGION']  # throw error if not set

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
            display_name='EFS and Glacier Job Notification Topic',
            topic_name='EfsAndGlacierTopic'
        )

        topic.add_subscription(subscriptions.EmailSubscription(self.NOTIFICATION_EMAIL, json=True))

        topic.apply_removal_policy(cdk.RemovalPolicy.DESTROY)

        # create ec2 security group to allow internal ssh
        ec2_sg = ec2.SecurityGroup(
            self, 'SshManagement',
            vpc=vpc,
            allow_all_outbound=True
        )

        ec2_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(22),
            description='ssh management access'
        )

        ec2_sg.apply_removal_policy(cdk.RemovalPolicy.DESTROY)

        # create user data for mounting ec2 instance and basic configuration
        user_data = ec2.UserData.for_linux()

        user_data.add_commands(
            "yum check-update -y", "yum upgrade -y", "yum install -y amazon-efs-utils", "yum install -y nfs-utils",
            "file_system_id_1=" + file_system.file_system_id, "efs_mount_point_1=/mnt/efs/fs1",
            "mkdir -p ${efs_mount_point_1}",
            "test -f /sbin/mount.efs && echo ${file_system_id_1}:/ ${efs_mount_point_1} efs defaults,_netdev >> /etc/fstab || "
            + "echo ${file_system_id_1}.efs." + self.REGION
            + ".amazonaws.com:/ ${efs_mount_point_1} nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport,_netdev 0 0 >> /etc/fstab",
            "mount -a -t efs,nfs4 defaults"
        )

        # create two ec2 instances; one for NFS and one for Worker
        app_server = ec2.Instance(
            self, id='AppServer',
            vpc=vpc,
            instance_name='app-server',
            instance_type=ec2.InstanceType('t2.xlarge'),
            machine_image=ec2.MachineImage.latest_amazon_linux(),
            key_name=self.KEY_PAIR_NAME,
            security_group=ec2_sg,
            user_data=user_data
        )

        app_server.user_data.add_commands(
            'sudo mkdir -p /mnt/efs/fs1/app-data',
            'sudo chown ec2-user:ec2-user /mnt/efs/fs1/app-data'
        )

        worker_server = ec2.Instance(
            self, id='WorkerServer',
            vpc=vpc,
            instance_name='worker-server',
            instance_type=ec2.InstanceType('t2.xlarge'),
            machine_image=ec2.MachineImage.latest_amazon_linux(),
            key_name=self.KEY_PAIR_NAME,
            security_group=ec2_sg,
            user_data=user_data
        )

        # create s3 glacier vault and post to SNS topic

        # create lambda -> start ec2 instance
