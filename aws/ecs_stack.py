from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_elasticloadbalancingv2 as elbv2,
)

class EcsStack(cdk.Stack):
    NODE_CONTAINER_REGISTRY_NAME   = "ghcr.io/jjisolo/ns-img:latest"
    MONGO_CONTAINER_REGISTRY_NAME  = "ghcr.io/jjisolo/ms-img:latest"

    NODE_CONTAINER_LOG_ENTITY_NAME  = "SirinNodeServer"
    MONGO_CONTAINER_LOG_ENTITY_NAME = "SirinMongoServer"

    HEALTH_CHECK_PATH = "/"

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.__init_vpc_and_clusters()

        self.__configure_ingress_rules()
        self.__init_docker_containers()

        self.__attach_alb()
        self.__init_health_check()
       
        # Configure the URL for the service
        cdk.CfnOutput(
            self,
            "SirinNodeServiceURL",
            value=f"http://{self.node_service.load_balancer.load_balancer_dns_name}"
        )

    def __init_vpc_and_clusters(self) -> None:

        # Create the VPC for the NodeJS container.
        self.public_vpc = ec2.Vpc(
            self,
            "SirinNodeStack",
            max_azs=2
        )
        
        # Create the VPC for the NodeJS container.
        self.private_vpc = ec2.Vpc(
            self,
            "SirinMongoStack",
            max_azs=2,
            nat_gateways=0
        )

        # Create the clusters based on the freshly baked VPC's
        self.public_cluster = ecs.Cluster(
            self,
            "SirinNodeCluster",
            vpc=self.public_vpc
        )

        self.private_cluster = ecs.Cluster(
            self,
            "SirinMongoCluster",
            vpc=self.private_vpc
        )

    def __init_docker_containers(self) -> None:

        # Create the Fargate task definition and attach the container
        # with the NodeJS app to it.
        self.nodejs_server_task_definition = ecs.FargateTaskDefinition(
            self,
            "SirinNodeTaskDefinition"
        )

        self.nodejs_server_container = self.nodejs_server_task_definition.add_container(
            "NodeServerContainer",
            image=ecs.ContainerImage.from_registry(EcsStack.NODE_CONTAINER_REGISTRY_NAME),
            logging=ecs.LogDrivers.aws_logs(stream_prefix=EcsStack.NODE_CONTAINER_LOG_ENTITY_NAME),
            port_mappings=[ecs.PortMapping(container_port=80)]
        )

        # Create the Fargate task definition and attach the container
        # with the Mongo database to it.
        self.mongo_server_task_definition = ecs.FargateTaskDefinition(
            self,
            "SirinMongoTaskDefinition"
        )

        self.mongo_server_container = self.mongo_server_task_definition.add_container(
            "NodeServerContainer",
            image=ecs.ContainerImage.from_registry(EcsStack.MONGO_CONTAINER_REGISTRY_NAME),
            logging=ecs.LogDrivers.aws_logs(stream_prefix=EcsStack.MONGO_CONTAINER_LOG_ENTITY_NAME),
            port_mappings=[ecs.PortMapping(container_port=27017)]
        )

    def __init_health_check(self) -> None:

        # Configure health check
        self.node_service.target_group.configure_health_check(
            path=EcsStack.HEALTH_CHECK_PATH,
            port='traffic-port',
            protocol=elbv2.Protocol.HTTP,
            interval=cdk.Duration.seconds(200),
            timeout=cdk.Duration.seconds(120),
            healthy_threshold_count=2,
            unhealthy_threshold_count=10
        )

    def __configure_ingress_rules(self) -> None:
        self.nodejs_server_security_group = ec2.SecurityGroup(
            self, "NodejsServerSecurityGroup", vpc=self.public_vpc
        )

        self.mongo_server_security_group = ec2.SecurityGroup(
            self, "MongoServerSecurityGroup", vpc=self.private_vpc
        )

        self.mongo_server_security_group.add_ingress_rule(
            self.nodejs_server_security_group,
            ec2.Port.tcp(27017),
            "Allow inbound access from the NodeJS server"
        )

    def __attach_alb(self) -> None:

        # Attach the ALB for the NodeJS container.
        self.node_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "SirinNodeService",
            cluster=self.public_cluster,
            task_definition=self.nodejs_server_task_definition,
            memory_limit_mib=4096,
            desired_count=1,
            public_load_balancer=True,
            security_groups=[self.nodejs_server_security_group],
        )

        # Attach the ALB for the MongoDB container.
        self.mongo_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "SirinMongoService",
            cluster=self.private_cluster,
            task_definition=self.mongo_server_task_definition,
            memory_limit_mib=4096,
            desired_count=1,
            public_load_balancer=True,
            security_groups=[self.mongo_server_security_group],
        )


