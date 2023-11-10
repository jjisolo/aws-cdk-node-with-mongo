from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ssm as ssm,
)


class EcsStack(cdk.Stack):
    NODE_CONTAINER_REGISTRY_NAME  = "ghcr.io/jjisolo/node:main"
    MONGO_CONTAINER_REGISTRY_NAME = "mongo"

    NODE_CONTAINER_LOG_ENTITY_NAME  = "SirinNodeServer"
    MONGO_CONTAINER_LOG_ENTITY_NAME = "SirinMongoServer"

    HEALTH_CHECK_PATH = "/"

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.__init_secrets_manager()
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

    def __init_secrets_manager(self) -> None:
        self.database_username = ssm.StringParameter.from_string_parameter_name(
            self, "MongoDbUsername",
            "/WorkTask/DatabaseUsername"
        ).string_value

        self.database_password = ssm.StringParameter.from_string_parameter_name(
            self, "MongoDbPassword",
            "/WorkTask/DatabasePassword"
        ).string_value

    def __init_vpc_and_clusters(self) -> None:
        # Create the VPC for the NodeJS container.
        self.vpc = ec2.Vpc(
            self,
            "SirinNodeStack",
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="PublicSubNet",
                    subnet_type=ec2.SubnetType.PUBLIC
                ),
                ec2.SubnetConfiguration(
                    name="PrivateSubNet",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                ),
            ]
        )

        # Create the clusters based on the freshly baked VPC
        self.cluster = ecs.Cluster(
            self,
            "SirinNodeCluster",
            vpc=self.vpc
        )

    def __init_docker_containers(self) -> None:
        # Create the Fargate task definition and attach the container
        # with the NodeJS app to it.
        self.server_task_definition = ecs.FargateTaskDefinition(
            self,
            "SirinNodeTaskDefinition"
        )

        self.mongo_server_container = self.server_task_definition.add_container(
            "MongoServerContainer",
            image=ecs.ContainerImage.from_registry(EcsStack.MONGO_CONTAINER_REGISTRY_NAME),
            logging=ecs.LogDrivers.aws_logs(stream_prefix=EcsStack.MONGO_CONTAINER_LOG_ENTITY_NAME),
            port_mappings=[ecs.PortMapping(container_port=27017)],
            environment={
                "MONGO_INITDB_ROOT_USERNAME": self.database_username,
                "MONGO_INITDB_ROOT_PASSWORD": self.database_password,
                "MONGO_INITDB_DATABASE"     : "mydatabase"
            }
        )

        self.nodejs_server_container = self.server_task_definition.add_container(
            "NodeServerContainer",
            image=ecs.ContainerImage.from_registry(EcsStack.NODE_CONTAINER_REGISTRY_NAME),
            logging=ecs.LogDrivers.aws_logs(stream_prefix=EcsStack.NODE_CONTAINER_LOG_ENTITY_NAME),
            port_mappings=[ecs.PortMapping(container_port=80)],
            environment={
                "MONGO_INITDB_ROOT_USERNAME": self.database_username,
                "MONGO_INITDB_ROOT_PASSWORD": self.database_password,
                "MONGO_INITDB_DATABASE"     : "mydatabase"
            }
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
        """
        self.nodejs_server_security_group = ec2.SecurityGroup(
            self, "NodejsServerSecurityGroup", vpc=self.vpc
        )

        self.mongo_server_security_group = ec2.SecurityGroup(
            self, "MongoServerSecurityGroup", vpc=self.vpc
        )

        self.mongo_server_security_group.add_ingress_rule(
            self.nodejs_server_security_group,
            ec2.Port.tcp(27017),
            "Allow inbound access from the NodeJS server"
        )
        """

    def __attach_alb(self) -> None:
        # Attach the ALB for the NodeJS container.
        self.node_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "SirinNodeService",
            cluster=self.cluster,
            task_definition=self.server_task_definition,
            memory_limit_mib=4096,
            desired_count=1,
            public_load_balancer=True,
            #security_groups=[self.nodejs_server_security_group],
        )
