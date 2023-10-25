#!/usr/bin/env python3

import aws_cdk as cdk

from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_efs as efs
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

gitlab_server_storage_security_group = ec2.SecurityGroup(
    stack,
    id="FileSystemSecurityGroup",
    vpc=cluster.vpc,
    security_group_name=f"GitlabMasterFilesystemSecurityGroup",
    description="Security Group to connect to EFS from the VPC"
)

gitlab_server_storage_security_group.add_ingress_rule(
    peer=ec2.Peer.ipv4(cluster.vpc.vpc_cidr_block),
    connection=ec2.Port.tcp(2049),
    description="Allow EC2 instances within the same VPC to connect to EFS"
)

gitlab_server_storage = efs.FileSystem(stack, "GitlabMasterStorage",
    vpc=cluster.vpc,
    security_group=gitlab_server_storage_security_group,
    performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
    throughput_mode=efs.ThroughputMode.BURSTING,
    vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
    lifecycle_policy=efs.LifecyclePolicy.AFTER_14_DAYS,
    removal_policy=cdk.RemovalPolicy.DESTROY,
)

gitlab_server_task_definition = ecs.FargateTaskDefinition(
    stack,
    "GitLab"
)

gitlab_server_task_definition.add_volume(
    name="GitLabVolume",
    efs_volume_configuration=ecs.EfsVolumeConfiguration(
        file_system_id=gitlab_server_storage.file_system_id,
        root_directory="/",
    )

)

gitlab_server_container = gitlab_server_task_definition.add_container(
    "GitLabServerContainer",
    image=ecs.ContainerImage.from_registry("gitlab/gitlab-ce:latest"),
    logging=ecs.LogDrivers.aws_logs(stream_prefix="GitLabServer"),
    port_mappings=[ecs.PortMapping(container_port=80)]
)

gitlab_server_container.add_mount_points(
    ecs.MountPoint(
        container_path="/var/gitlab_home",
        source_volume="GitLabVolume",
        read_only=False
    )
)

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
    path='/users/sign_in',
    port='traffic-port',
    protocol=elbv2.Protocol.HTTP,
    interval= cdk.Duration.seconds(200),
    timeout = cdk.Duration.seconds(120),
    healthy_threshold_count  = 10,
    unhealthy_threshold_count= 10
)

cdk.CfnOutput(
    stack,
    "GitlabServiceURL",
    value=f"http://{gitlab_service.load_balancer.load_balancer_dns_name}"
)

app.synth()
