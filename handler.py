"""
This cripts will lunch new EC2 intances, run a script, get the result then destroy it.
"""

import logging
import boto3
import sys
import yaml
import argparse
from classes.ec2_instance_manager import Ec2InstanceManager
from classes.ec2_ssm import Ec2Ssm
from classes.ec2_ssm_remote_commands_exception import Ec2SsmRemoteCommandsException

def initialize_logger():
    # specify the logging format
    level      = "INFO"
    log_format = "%(asctime)s - %(levelname)s - %(module)s - %(message)s"

    # set up default logging settings
    logging.basicConfig(level=level, format=log_format)

def main():
    # initialize the logger
    initialize_logger()

    # get configurations
    f = open("config/settings.yml")
    config = yaml.safe_load(f)
    f.close()

    #Get the remote command to execute
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--command", help="list of commands separate by spaces", nargs='+', default=[], dest='commands', required=True)
    parser.add_argument("-p", "--project", help="project name", type = str, dest='project_name', required=True)
    parser.add_argument("-a", "--ami-id", help="Base image ami ID", type = str, dest='ami_id', required=True)
    args = parser.parse_args()

    try:
        # Creating EC2 instance manager obejct
        ec2_manager = Ec2InstanceManager(
            aws_region               = config["aws"]["region"],
            aws_instance_name_prefix = args.project_name,
            aws_instance_disk_size   = config["aws"]["ec2_instance"]["disk_size"],
            aws_instance_type        = config["aws"]["ec2_instance"]["type"],
            aws_ami_id               = args.ami_id,
            aws_iam_arn              = config["aws"]["ec2_instance"]["iam_arn"],
            aws_vpc_id               = config["aws"]["ec2_instance"]["vpc_id"],
            aws_subnet_id            = config["aws"]["ec2_instance"]["subnet_id"]
        )
        # Creating the security group
        remote_instance_id = ec2_manager.create_security_group()
        # Launching the ec2 instance
        remote_instance_id = ec2_manager.create_ec2_instance()
        # Creating EC2 SSM obejct
        ec2_ssm = Ec2Ssm(
            aws_region=config["aws"]["region"],
            ssm_cmd_output_s3_bucket_name = config["aws"]["ssm"]["output_s3_bucket_name"],
            aws_instance_name_prefix = args.project_name,
        )
        # Check if SSM agent is up and wait for it if needed
        ec2_ssm.wait_for_ssm_agent(remote_instance_id)
        # Run command on remote instance
        ec2_ssm.send_run_command(
            instance_id = remote_instance_id,
            commands = args.commands
        )
        # Wait for command to finish executing and get result
        ec2_ssm.wait_for_command_to_finish(
            instance_id = remote_instance_id,
        )
    except Ec2SsmRemoteCommandsException as err:
        logging.error("Remote code execution failed: "+ str(err))
        sys.exit(1)
    except Exception as err:
        logging.error("Something when wrong: "+ str(err))
        sys.exit(1)
    finally:
        logging.info("Cleanup environment")
        # Terminate the ec2 instance if created
        ec2_manager.terminate_ec2_instance()
        # Delete the security group if created
        ec2_manager.delete_security_group()

# main entry point
if __name__ == "__main__":
    main()
