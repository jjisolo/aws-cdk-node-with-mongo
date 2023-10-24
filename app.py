#!/usr/bin/env python3

import aws_cdk as cdk

from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns
from aws_cdk import aws_elasticloadbalancingv2 as elbv2

app   = cdk.App()
stack = cdk.Stack(app, "SirinStack")

# Cluster
vpc = ec2.Vpc(
    stack,
    "Vpc0",
    max_azs=3
)

cluster = ecs.Cluster(
    stack,
    "Cluster",
    vpc=vpc
)

# GitLab
gitlab_server_task_definition = ecs.FargateTaskDefinition(
    stack,
    "GitLab"
)

gitlab_server_container = gitlab_server_task_definition.add_container(
    "GitLabServerContainer",
    image=ecs.ContainerImage.from_registry("gitlab/gitlab-ce:latest"),
    logging=ecs.LogDrivers.aws_logs(stream_prefix="GitLabServer"),
    port_mappings=[ecs.PortMapping(container_port=80)]
)

"""
gitlab_volume_config = "gitlab-config"
gitlab_volume_logs   = "gitlab-logs"
gitlab_volume_data   = "gitlab-data"

gitlab_server_container.add_mount_points(
    ecs.MountPoint(
        container_path="/etc/gitlab",
        source_volume=gitlab_volume_config,
        read_only=False
    ),
    ecs.MountPoint(
        container_path="/var/log/gitlab",
        source_volume=gitlab_volume_logs,
        read_only=False
    ),
    ecs.MountPoint(
        container_path="/var/opt/gitlab",
        source_volume=gitlab_volume_data,
        read_only=False
    ),
)
"""

gitlab_service = ecs_patterns.ApplicationLoadBalancedFargateService(
    stack,
    "GitLabService",
    cluster=cluster,
    task_definition=gitlab_server_task_definition,
    memory_limit_mib=4096,
    desired_count=1,
    public_load_balancer=True,
)

gitlab_service.target_group.configure_health_check(
    path='/users/signin',
    port='traffic-port',
    protocol=elbv2.Protocol.HTTP,
    interval=cdk.Duration.seconds(30),
    timeout=cdk.Duration.seconds (5 ),
    healthy_threshold_count  = 3,
    unhealthy_threshold_count= 3
)

cdk.CfnOutput(
    stack,
    "GitlabServiceURL",
    value=f"http://{gitlab_service.load_balancer.load_balancer_dns_name}"
)

app.synth()
