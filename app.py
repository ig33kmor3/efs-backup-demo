#!/usr/bin/env python3
import os
from aws_cdk import core as cdk

from iac.stack import EfsBackupDemoStack

app = cdk.App()
EfsBackupDemoStack(
    app, 'EfsBackupDemoStack',
    env={
        'account': os.environ['ACCOUNT_ID'],
        'region': os.environ['REGION']
    }
)

app.synth()
