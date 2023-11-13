# Overview
This repository is a part of my training with AWS CDK. 

It is used to push the Amazon CloudFormation stack template
to the Amazon Web Services Cloud. The stack contains the
Fargate Task which executes two docker containers: one of
them is MongoDB and another is the NodeJS express application

This repository contains GitHub pipelines which are building
two docker containers that are described above, deploying
them to the GitHub private container registry and then to the
AWS Cloud.

This AWS Stack contains such services:
* ECS
* EC2
* IAM
* Logs
* Lambda
* Healthcheck
* ElasticLoadBalancing
* SecretsManager

# Building
To build this project, you need aws-cli/aws-sdk application installed
on your host machine.

First, install the requirements:
```
$ pip3 install -r requirements.txt 
```

Next login into your AWS IAM user:
```
$ aws configure
```

And, finally, bootstrap and deploy this stack.
```
$ cdk bootstrap
$ cdk deploy
```


