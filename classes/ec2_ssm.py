#!/usr/bin/python
## Create a EC2 instance using boto3

import boto3
from botocore.errorfactory import ClientError
import sys
import time
import logging
from classes.ec2_ssm_remote_commands_exception import Ec2SsmRemoteCommandsException

class Ec2Ssm():
    """This class will allow remote code execution on EC2 machines"""

    def __init__(self, aws_region, ssm_cmd_output_s3_bucket_name, aws_instance_name_prefix):
        self.command_id = None
        self.command_remote_invocation_timeout = 900 # timeout for commands have been triggraded
        self.command_execution_timeout = 86400 # timeout for all commands have to complete in #Max 48hours - 172800
        self.command_status_check_inerval = 60
        self.command_ssm_agent_check_status_timeout = 86400 # Wait the agent to start job (the jobs can be queued if you hit AWS soft limit) # set to 10 hours
        self.document_name = "AWS-RunPowerShellScript"
        self.command_output_bucket_name = ssm_cmd_output_s3_bucket_name
        self.instance_name_prefix = aws_instance_name_prefix

        # Create connection client
        self.ssm = boto3.client('ssm', aws_region)
        self.s3 = boto3.resource('s3')

    def wait_for_ssm_agent(self, instance_id):
        logging.info("Waiting for SSM agent to start...")
        loop_time = 0
        while True:
            instance_found = self.ssm.describe_instance_information(
            Filters=[
                {
                    'Key': 'InstanceIds',
                    'Values': [ instance_id ]
                }
            ]
            )['InstanceInformationList']
            if instance_found:
                logging.info("###### SSM agent Status: Up ...")
                break
            elif loop_time >= self.command_ssm_agent_check_status_timeout:
                raise Exception("Timeout SSM agent after "+ str(self.command_ssm_agent_check_status_timeout) +"s...")
            time.sleep(self.command_status_check_inerval)
            loop_time += self.command_status_check_inerval


    def send_run_command(self, instance_id, commands):
        logging.info("Sending command to remote machine...")
        ssm_command = self.ssm.send_command(
            InstanceIds=[instance_id],
            MaxConcurrency= '1000',
            DocumentName=self.document_name,
            TimeoutSeconds=self.command_remote_invocation_timeout,
            Parameters={
                'commands': commands,
                'executionTimeout': [str(self.command_execution_timeout)]
            },
            OutputS3BucketName=self.command_output_bucket_name,
            OutputS3KeyPrefix=self.instance_name_prefix,
            CloudWatchOutputConfig={
                'CloudWatchLogGroupName': self.instance_name_prefix,
                'CloudWatchOutputEnabled': True
            }
        )

        self.command_id = ssm_command["Command"]["CommandId"]


    def wait_for_command_to_finish(self, instance_id):
        logging.info("Waiting for command to finish executing...")
        time.sleep(2)
        while True:
            ssm_command_resp = self.ssm.get_command_invocation(
                CommandId=self.command_id,
                InstanceId=instance_id
            )
            ssm_command_status = ssm_command_resp.get('Status')
            if self.is_in_progress(ssm_command_status):
                time.sleep(self.command_status_check_inerval)
            elif self.is_success(ssm_command_status):
                logging.info("###### Status: " +ssm_command_status +"...")
                self.print_outputs(ssm_command_resp)
                break
            else:
                logging.info("###### Status: " +ssm_command_status +"...")
                self.print_outputs(ssm_command_resp)
                raise Ec2SsmRemoteCommandsException("Command execution failed")

    def is_in_progress(self, status):
        logging.debug("###### Status: " +status +"...")
        return status in ['Pending', 'InProgress', 'Delayed']

    def is_success(self, status):
        return status == 'Success'

    def read_s3_file(self, file_key):
        try:
            s3_file = self.s3.Object(self.command_output_bucket_name, file_key)
            return s3_file.get()['Body'].read().decode("utf-8")
        except self.s3.meta.client.exceptions.NoSuchKey:
            return ""

    def print_outputs(self, response):
        self.status('stdout output:')
        logging.info('\n' + self.read_s3_file(response.get('StandardOutputUrl').split("/", 4)[4]))
        self.status('stderr output:')
        logging.info('\n' + self.read_s3_file(response.get('StandardErrorUrl').split("/", 4)[4]))
        self.status('full logs available on S3:')
        self.status('stdout: ' + response.get('StandardOutputUrl'))
        self.status('stderr: ' + response.get('StandardErrorUrl'))

    def status(self, message):
        logging.info('---> ' + message)
