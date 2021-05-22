import os

from aws_cdk import (
    core as cdk,
    aws_efs as efs,
    aws_ec2 as ec2,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_iam as iam
)


class EfsBackupDemoStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # set variables
        vpc_id = os.environ['VPC_ID']  # throw error if not set
        notification_email = os.environ['NOTIFICATION_EMAIL']  # throw error if not set
        key_pair_name = os.environ['KEY_PAIR_NAME']  # throw error if not set
        region = os.environ['REGION']  # throw error if not set
        efs_bucket_name = f'efs-backup-{cdk.Stack.of(self).account}'
        worker_bucket_name = os.environ['WORKER_BUCKET_NAME']  # throw error if not set ; location of worker script

        # import existing cloud infrastructure
        vpc = ec2.Vpc.from_lookup(
            self, 'Vpc',
            vpc_id=vpc_id
        )

        worker_s3_bucket = s3.Bucket.from_bucket_name(
            self, 'WorkerS3Bucket',
            bucket_name=worker_bucket_name
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
        email_topic = sns.Topic(
            self, 'EFSandGlacierJobsTopic',
            display_name='EFS and Glacier Job Notification Topic',
            topic_name='EfsAndGlacierTopic'
        )

        email_topic.add_subscription(subscriptions.EmailSubscription(notification_email))
        email_topic.apply_removal_policy(cdk.RemovalPolicy.DESTROY)

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
            "mkdir -p ${efs_mount_point_1}", "test -f /sbin/mount.efs && echo ${file_system_id_1}:/ "
            + "${efs_mount_point_1} efs defaults,_netdev >> /etc/fstab || echo ${file_system_id_1}.efs." + region
            + ".amazonaws.com:/ ${efs_mount_point_1} nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,"
            + "timeo=600,retrans=2,noresvport,_netdev 0 0 >> /etc/fstab", "mount -a -t efs,nfs4 defaults"
        )

        # create s3 bucket with glacier lifecycle policy
        efs_s3_bucket = s3.Bucket(
            self, 'EfsS3Backup',
            bucket_name=efs_bucket_name,
            auto_delete_objects=True,
            versioned=True,
            enforce_ssl=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id='budget-lifecycle',
                    enabled=True,
                    abort_incomplete_multipart_upload_after=cdk.Duration.days(30),
                    noncurrent_version_transitions=[
                        s3.NoncurrentVersionTransition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=cdk.Duration.days(60)
                        ),
                        s3.NoncurrentVersionTransition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=cdk.Duration.days(90)
                        ),
                        s3.NoncurrentVersionTransition(
                            storage_class=s3.StorageClass.DEEP_ARCHIVE,
                            transition_after=cdk.Duration.days(365)
                        )
                    ],
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=cdk.Duration.days(60)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=cdk.Duration.days(90)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.DEEP_ARCHIVE,
                            transition_after=cdk.Duration.days(365)
                        )
                    ]
                )
            ],
            removal_policy=cdk.RemovalPolicy.DESTROY
        )

        # create two ec2 instances; one for NFS and one for Worker to perform backups
        app_server = ec2.Instance(
            self, id='AppServer',
            vpc=vpc,
            instance_name='app-server',
            instance_type=ec2.InstanceType('t2.xlarge'),
            machine_image=ec2.MachineImage.latest_amazon_linux(),
            key_name=key_pair_name,
            security_group=ec2_sg,
            user_data=user_data
        )

        app_server.user_data.add_commands(
            'sudo mkdir -p /mnt/efs/fs1/app-data',
            'sudo chown -R ec2-user:ec2-user /mnt/efs/fs1/app-data'
        )

        worker_server = ec2.Instance(
            self, id='WorkerServer',
            vpc=vpc,
            instance_name='worker-server',
            instance_type=ec2.InstanceType('t2.xlarge'),
            machine_image=ec2.MachineImage.latest_amazon_linux(),
            key_name=key_pair_name,
            security_group=ec2_sg,
            user_data=user_data
        )

        worker_server.user_data.add_s3_download_command(
            bucket=worker_s3_bucket,
            bucket_key='ec2_worker.py',
            local_file='/home/ec2-user/ec2_worker.py',
        )

        worker_server.user_data.add_commands(
            "sudo yum update -y && sudo yum install python38 -y",
            f"echo 'export BUCKET_NAME={efs_s3_bucket.bucket_name}' >> /home/ec2-user/.bashrc",
            f"echo 'export EMAIL_TOPIC_ARN={email_topic.topic_arn}' >> /home/ec2-user/.bashrc",
            "echo 'export SOURCE_DIR=/mnt/efs/fs1/app-data' >> /home/ec2-user/.bashrc"
        )

        # grant ec2 worker permissions to interact with s3 and sns
        efs_s3_bucket.grant_read_write(worker_server)
        worker_s3_bucket.grant_read(worker_server)
        email_topic.grant_publish(worker_server)

        # create lambda -> start ec2 instance and run worker backup script
        lambda_function = _lambda.Function(
            self, 'LambdaWorker',
            function_name='LambdaWorker',
            description='Orchestrate EFS backups',
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler='lambda_worker.handler',
            code=_lambda.Code.from_asset('lambda'),
            memory_size=256,
            environment={
                'INSTANCE_ID': f'{worker_server.instance_id}'
            }
        )

        # add permissions to allow lambda to interact with ec2 instances
        lambda_function.role.add_to_principal_policy(
            iam.PolicyStatement(
                actions=[
                    'ec2:StartInstances',
                    'ec2:StopInstances'
                ],
                resources=[
                    f'arn:aws:ec2:*:{cdk.Stack.of(self).account}:instance/*'
                ]
            )
        )

        # create SNS topic and subscription for lambda to manage ec2 worker
        lambda_topic = sns.Topic(
            self, 'LambdaWorkerTopic',
            display_name='Topic to Trigger Lambda Worker for EC2',
            topic_name='LambdaWorkerTopic'
        )

        lambda_topic.add_subscription(subscriptions.LambdaSubscription(lambda_function))
        lambda_topic.grant_publish(worker_server)
        lambda_topic.apply_removal_policy(cdk.RemovalPolicy.DESTROY)
        worker_server.user_data.add_commands(
            f"echo 'export LAMBDA_TOPIC_ARN={lambda_topic.topic_arn}' >> /home/ec2-user/.bashrc"
        )
