# AWS EFS IaC and Backup to S3 Glacier

## Setup

Set the following environment variables:

Local IaC Variables:

```bash
export WORKER_AWS_PROFILE=XXX
export VPC_ID=XXX
export ACCOUNT_ID=XXX
export REGION=XXX
export KEY_PAIR_NAME=XXX
export NOTIFICATION_EMAIL=XXX
```

EC2 Worker Variables (Automatically Set by IAC)

```bash
export SOURCE_DIR=XXX
export BUCKET_NAME=XXX
```

Attach IAM role to EC2 instance that can communicate with S3 Glacier and SNS Topic.

## Development

Install the CDK for IaC:

```
$ npm install -g aws-cdk
$ cdk --version
```

Activate MacOS/Linux virtual environment:

```
$ source .venv/bin/activate
```

Activate Windows virtual environment:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies:

```
$ pip install -r requirements.txt
```

If dependencies are changed, you can update dependency requirements:

```
$ pip freeze > requirements.txt
```

Update dependencies currently installed:

```
$ pip install -r requirements.txt --upgrade
```

AWS cli get job status:

```
$ aws glacier describe-job --account-id XXX --vault-name XXX --job-id XXX--profile XXX
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

## Deployment

* `cdk ls`                         list all stacks in the app
* `cdk synth`                      emits the synthesized CloudFormation template
* `cdk deploy --profile XXX`       deploy this stack to your default AWS account/region
* `cdk diff`                       compare deployed stack with current state
* `cdk docs`                       open CDK documentation
