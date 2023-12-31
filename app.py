#!/usr/bin/env python3

import aws_cdk as cdk
from aws.ecs_stack import EcsStack

app       = cdk.App()
ecs_stack = EcsStack(app, "SirinNodeStack4")
app.synth()
