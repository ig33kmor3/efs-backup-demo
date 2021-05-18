# AWS EFS IaC and Backup to S3 Glacier

## Setup

Set the following environment variables:

```bash
export WORKER_INSTANCE_ID=XXX
export WORKER_AWS_PROFILE=XXX
export VAULT=XXX
export SOURCE_DIR=XXX
```

## Development 

Install the CDK for IaC:

```
npm install -g aws-cdk
cdk --version
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
pip install -r requirements --upgrade
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
