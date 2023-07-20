"""
Docker Python SDK to run and deploy Terraform code in current directory.

Usage examples:

# Running with no terraform variables
run_terraform_command(
    "plan", "state-file-bucket", "eu-west-1"
    )

# Running with terraform variables    
variables = {
    "bucket_tag_name": "can_be_deleted_now",
    "bucket_tag_env": "dev"
}
    
run_terraform_command(
    "apply -auto-approve", "state-file-bucket", "eu-west-1", variables
    )
"""

import docker
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import os
import sys


def check_aws_credentails():
    """
    Checks if aws credentials using aws configure are set up. Returns false if no
    """
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        if credentials is None:
            print("AWS credentials are not configured. Use 'aws configure'.")
            return False
    except NoCredentialsError:
        print("AWS credentials are not configured. Use 'aws configure'.")
        return False


def check_s3_bucket(bucket_name, region):
    """
    Checks if s3 bucket exists, if doesn't creates it and initate terraform
    """
    s3 = boto3.client("s3", region_name=region)

    try:
        s3.head_bucket(Bucket=bucket_name)
    except s3.exceptions.ClientError as e:
        # The bucket does not exist, create it
        if e.response["Error"]["Code"] == "404":
            print(f'State file bucket {bucket_name} does not exist". Creating...')
            try:
                s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": region},
                )
                print(f"State file bucket {bucket_name} created successfully.")
            except Exception as err:
                print(f"Error creating S3 bucket: {str(err)}")
                sys.exit(1)

            # Run terraform init to setup    
            run_terraform_command(
                f"init -reconfigure -backend-config='bucket={bucket_name}' -backend-config='region={region}'",
                bucket_name,
                region,
            )                  
        else:
            print(f"Error checking S3 bucket: {e}")
            sys.exit

def delete_s3_bucket(bucket_name):
    """
    Deletes an S3 bucket used for Terraform state file storing
    after Terraform destroy is run.
    """
    s3 = boto3.client("s3")
    try:
        # Delete all objects in the bucket
        response = s3.list_objects_v2(Bucket=bucket_name)
        if "Contents" in response:
            objects = [{"Key": obj["Key"]} for obj in response["Contents"]]
            s3.delete_objects(Bucket=bucket_name, Delete={"Objects": objects})

        # Delete the bucket
        print(f"Deleting state file bucket: {bucket_name}")
        s3.delete_bucket(Bucket=bucket_name)
        print(f"Successfully deleted bucket: {bucket_name}")
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "NoSuchBucket":
            print(f"Failed to delete state file bucket: {bucket_name} does not exist: ")
        elif error_code == "AccessDenied":
            print(
                f"Failed to delete state file bucket: Access denied, unable to delete {bucket_name}"
            )
        else:
            print(f"Error deleting state file bucket {bucket_name}: {error_code} - {e}")


def run_terraform_command(command, s3_state, region, vars=None, no_vars=False):
    """
    Runs terraform command. E.g. plan, apply, destroy and so on
    """
    if check_aws_credentails() == False:
        return
    check_s3_bucket(s3_state, region)
    client = docker.from_env()
    volumes = {
        f"{os.getcwd()}": {"bind": "/workspace", "mode": "rw"},
        f"{os.path.expanduser('~')}/.aws": {"bind": "/root/.aws", "mode": "rw"},
    }

    if no_vars == True:
        # if true, pass only command
        passed_commands = command
    else:
        # Check if vars are specified, if yes add arguments
        if vars is None:
            variable_args = ""
        else:
            variable_args = " ".join(
                [f"-var='{key}={value}'" for key, value in vars.items()]
            )
        passed_commands = f"{command} -var='aws_region={region}' {variable_args}"

    try:
        # Run the terraform command
        container = client.containers.run(
            "frankenk/terraform-pip3:latest",
            command=passed_commands,
            volumes=volumes,
            working_dir="/workspace",
            remove=True,
            stdin_open=True,
            tty=True,
        )
        output = container.decode()

        # Delete the bucket after destroying
        if command == "destroy" or command == "destroy -auto-approve -input=false":
            delete_s3_bucket(s3_state)
        return output
    
    except docker.errors.ContainerError as e:
        print(f"Failed to run command: {e}")
        return None    