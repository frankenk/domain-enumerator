"""
Runs ECS tasks depending on commands received from 
EventBridge json data
"""

import boto3
from botocore.exceptions import ClientError
import json
import os
import re

def run_tasks(commands_passed_to_container):
    """
    Runs the actual task with the commands.

    Args:
        commands_passed_to_container (list): The list of commands to be passed to the container.

    Returns:
        dict: The response from running the task.
    """
    ecs = boto3.client('ecs',region_name="eu-west-1")
    cluster_name = 'tf_domain_enumerator' # hardcored cluster name
    try:
        response = ecs.run_task(
            cluster=cluster_name,
            taskDefinition=os.environ['ECS_TASK_DEFINITION_ARN'],
            launchType='FARGATE',
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': [
                        os.environ['DEFAULT_SUBNET'],
                    ],
                    'securityGroups': [
                        os.environ['DEFAULT_SECURITY_GROUP'],
                    ],
                    'assignPublicIp': 'ENABLED'            
                }
            },
            overrides={
                'containerOverrides': commands_passed_to_container
            }
        )
    except ClientError as err:
        print(f"ERROR: error while trying to run task {err}")
    else:
        return response

def retrieve_domains(bucket_name):
    """
    Retrieves the domains "targets" from S3.

    Args:
        bucket_name (str): The name of the S3 bucket.

    Returns:
        list: The list of domains.
    """
    s3 = boto3.client('s3')
    file_name = 'targets.txt'
    try:
        response = s3.get_object(Bucket=bucket_name, Key=file_name)
        domains = response['Body'].read().decode().splitlines()
        return domains        
    except ClientError as err:
        print(f"ERROR: error while retrieving domains {err}")

def run_tools(data, domains):
    """
    Passes commands to the run_tasks function.

    Args:
        data (dict): The commands data.
        domains (list): The list of domains.
    """   
    for domain in domains:
        commands_passed_to_container = []
        for i in range(len(data["tool_names"])):
            tool_name = data["tool_names"][i]
            tool_command = data["tool_commands"][i] 
            commands_passed_to_container.append({
                "name": tool_name,
                "command": tool_command.split() + [domain] 
            })
        response = run_tasks(commands_passed_to_container)
        task_id = response['tasks'][0]['taskArn']
        print(f'INFO: Started task {task_id} for {domain}')

def lambda_handler(event, context):
    try:
        s3_bucket_name =  re.search(r'(.+)\.s3', os.environ['DATA_S3']).group(1)
        domains = retrieve_domains(s3_bucket_name)
        run_tools(event, domains)
    except Exception as err:
        print(f"ERROR: error occurred in the lambda_handler: {err}")
        return {
            'statusCode': 500,
            'body': json.dumps(str(err))
        }

#Test using this:
# data = {
#     "tool_names":["amass", "subfinder"],
#     "tool_commands":["enum -timeout 1 -d","-oJ -silent -d"]
# }
