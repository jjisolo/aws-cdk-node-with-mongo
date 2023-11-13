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
    """
    This stack declares the template that
    is needed for the AWS CloudFormation service.
    """

    NODE_CONTAINER_REGISTRY_NAME  = "ghcr.io/jjisolo/node:main"
    MONGO_CONTAINER_REGISTRY_NAME = "mongo"

    NODE_CONTAINER_LOG_ENTITY_NAME  = "SirinNodeServer"
    MONGO_CONTAINER_LOG_ENTITY_NAME = "SirinMongoServer"

    HEALTH_CHECK_PATH = "/"

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """
        This function is a constructor for this class instance.
        
        It retrieves data from the secrets manager, intilizes 
        the VPC and cluster and Fargate instance with two containers
        inside of it. Also it configures ALB and HealthCheck.
        """

        super().__init__(scope, construct_id, **kwargs)

        self.__init_secrets_manager()
        self.__init_vpc_and_clusters()
        self.__init_docker_containers()

        self.__attach_alb()
        self.__init_health_check()

        # Configure the URL for the service
        cdk.CfnOutput(
            self,
            "SirinNodeServiceURL",
            value=f"http://{self.load_balancer.load_balancer_dns_name}"
        )

    def __init_secrets_manager(self) -> None:
        """
        This function is used to retrieve the data from the AWS
        secrets manager.
        """

        self.database_username = ssm.StringParameter.from_string_parameter_name(
            self, "MongoDbUsername",
            "/WorkTask/DatabaseUsername"
        ).string_value

        self.database_password = ssm.StringParameter.from_string_parameter_name(
            self, "MongoDbPassword",
            "/WorkTask/DatabasePassword"
        ).string_value

    def __init_vpc_and_clusters(self) -> None:
        """
        This function is used to initialize the VPC with
        two subntes inside of it: one is private and another
        is public.
        """

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
        """
        This function initializng the Fargate task with
        two docker containers(one of the is MongoDB and
        another is NodeJS app, that i wrote on my own and
        deploued to the github container registry).
        """

        # Create the Fargate task definition and attach the container
        # with the NodeJS app to it.
        self.server_task_definition = ecs.FargateTaskDefinition(
            self,
            "SirinNodeTaskDefinition"
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

        self.mongo_server_container = self.server_task_definition.add_container(
            "MongoServerContainer",
            image=ecs.ContainerImage.from_registry(EcsStack.MONGO_CONTAINER_REGISTRY_NAME),
            logging=ecs.LogDrivers.aws_logs(stream_prefix=EcsStack.MONGO_CONTAINER_LOG_ENTITY_NAME),
            environment={
                "MONGO_INITDB_ROOT_USERNAME": self.database_username,
                "MONGO_INITDB_ROOT_PASSWORD": self.database_password,
                "MONGO_INITDB_DATABASE"     : "mydatabase"
            }
        )


    def __init_health_check(self) -> None:
        """
        This function is used to initialize the HealthCheck for
        the fartgate task definition.
        """

        # Configure health check
        self.target_group1.configure_health_check(
            path=EcsStack.HEALTH_CHECK_PATH,
            port='traffic-port',
            protocol=elbv2.Protocol.HTTP,
            interval=cdk.Duration.seconds(200),
            timeout=cdk.Duration.seconds(120),
            healthy_threshold_count=2,
            unhealthy_threshold_count=10
        )

    def __attach_alb(self) -> None:
        """
        This function is used to attach the ALB to the Fargate
        service.
        """

        self.load_balancer = elbv2.ApplicationLoadBalancer(self, "MyLoadBalancer", vpc=self.vpc, internet_facing=True)
        self.listener = self.load_balancer.add_listener("MyListener", port=80)
        self.fargate_service = ecs.FargateService(self, "MyFargateService1", cluster=self.cluster, task_definition=self.server_task_definition)
        self.target_group1 = self.listener.add_targets("TargetGroup1", port=80, targets=[self.fargate_service])
        self.listener.add_target_groups("DefaultRule", target_groups=[self.target_group1])
