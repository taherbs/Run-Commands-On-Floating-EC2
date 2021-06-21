#!/usr/bin/python
## Create a EC2 instance using boto3

import boto3
from botocore.config import Config
import sys
import time
import logging
import random
import string

class Ec2InstanceManager():

    def __init__(self, aws_region, aws_instance_name_prefix, aws_instance_disk_size, aws_instance_type, aws_ami_id, aws_iam_arn, aws_vpc_id,aws_subnet_id):
        letters = string.ascii_lowercase
        random_txt = ''.join(random.choice(letters) for i in range(8))
        self.aws_region = aws_region
        self.aws_instance_name_prefix = aws_instance_name_prefix
        self.aws_instance_name = aws_instance_name_prefix + "-" + random_txt
        self.aws_instance_id = None
        self.aws_resources_creator_name = "boto3-rendering-farm-genertor"
        self.aws_instance_disk_size = aws_instance_disk_size
        self.aws_instance_type = aws_instance_type
        self.aws_ami_id = aws_ami_id
        self.aws_iam_arn = aws_iam_arn
        self.aws_instance_security_group_name = aws_instance_name_prefix + "-sg-" + random_txt
        self.aws_instance_security_group_id = None
        self.aws_instance_ingress_ports = [ 3389, 5985, 5986 ]
        self.aws_instance_ingress_cidr_ip = "0.0.0.0/0"
        self.aws_vpc_id = aws_vpc_id
        self.aws_subnet_id = aws_subnet_id

        # Create connection client
        config = Config(
            region_name = self.aws_region,
            retries = dict(
                max_attempts = 30
            )
        )
        self.client = boto3.client('ec2', config=config)
        self.resource = boto3.resource('ec2', config=config)

    def create_security_group(self):
            logging.info("Creating the security group with the name : "+ self.aws_instance_security_group_name )
            sg = self.client.create_security_group(
                GroupName=self.aws_instance_security_group_name,
                Description=self.aws_instance_security_group_name,
                VpcId=self.aws_vpc_id
            )
            self.client.create_tags(
                Resources=[sg["GroupId"]],
                Tags=[
                    {
                        'Key': 'CreatedBy',
                        'Value': self.aws_resources_creator_name
                    }
                ]
            )

            logging.info("Setting security group ingress ports" )
            for port in self.aws_instance_ingress_ports:
                self.client.authorize_security_group_ingress(
                    GroupId=sg["GroupId"],
                    IpProtocol="tcp",
                    CidrIp=self.aws_instance_ingress_cidr_ip,
                    FromPort=port,
                    ToPort=port

                )

            self.aws_instance_security_group_id = sg["GroupId"]
            logging.info("Successfully created the security group with the inbound port  : "+ str(self.aws_instance_ingress_ports))


    def delete_security_group(self):
        logging.info("Deleting the security group with the name : "+ self.aws_instance_security_group_name )
        if self.aws_instance_security_group_id:
            sg = self.client.delete_security_group(
                GroupId=self.aws_instance_security_group_id,
            )
            logging.info("Successfully deleted security group with the name : "+ self.aws_instance_security_group_name )
        else:
            logging.info("Nothing to delete - security group with the name : "+ self.aws_instance_security_group_name +" does not exist.")


    def create_ec2_instance(self):
        logging.info("Creating EC2 instance '"+ self.aws_instance_name+"'" )
        instance =self.resource.create_instances(
                        ImageId=self.aws_ami_id,
                        InstanceType=self.aws_instance_type,
                        MinCount=1,
                        MaxCount=1,
                        NetworkInterfaces= [{
                            'DeviceIndex': 0,
                            'SubnetId': self.aws_subnet_id,
                            'AssociatePublicIpAddress': False,
                            'Groups': [
                                self.aws_instance_security_group_id,
                            ]
                        }],
                        IamInstanceProfile={
                            'Arn': self.aws_iam_arn
                        },
                        BlockDeviceMappings=[
                            {
                                'DeviceName': '/dev/sda1',
                                'Ebs': {
                                    'DeleteOnTermination': True,
                                    'VolumeSize': int(self.aws_instance_disk_size)
                                }
                            }
                        ]
                    )[0]
        time.sleep(2)
        instance.create_tags(
            Tags=
                [
                    {
                        'Key':'Name',
                        'Value':self.aws_instance_name
                    },
                    {
                        'Key':'CreatedBy',
                        'Value':self.aws_resources_creator_name
                    }
                ]
        )
        instance.wait_until_running()
        volume = list(instance.volumes.all())[0]
        volume.create_tags(
            Tags=
                [
                    {
                        'Key':'Name',
                        'Value':self.aws_instance_name
                    },
                    {
                        'Key':'CreatedBy',
                        'Value':self.aws_resources_creator_name
                    }
                ]
        )
        self.aws_instance_id = instance.id
        logging.info('Instance created and running ...')
        logging.info('Created instanceID: '+ self.aws_instance_id +' ...')
        logging.info('Created instance private IP address: '+ instance.private_ip_address +' ...')
        return self.aws_instance_id


    def terminate_ec2_instance(self):
        logging.info("Terminating the EC2 instance: '"+ self.aws_instance_name+"'" )
        if self.aws_instance_id:
            instance = self.resource.Instance(self.aws_instance_id)
            instance.terminate()
            instance.wait_until_terminated()
            logging.info("EC2 instance with the name : "+ self.aws_instance_name +" terminated" )
        else:
            logging.info("AWS instanceID not defined - probably that the instance has not been created yet - nothing to do.")
