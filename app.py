#!/usr/bin/env python3

import aws_cdk as cdk

from aws.aws_stack import AwsStack


app = cdk.App()
AwsStack(app, "AwsStack")

app.synth()
