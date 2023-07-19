import boto3
import sys
import argparse
from argparse import RawTextHelpFormatter
import terraform_deployer
import re
from datetime import datetime

def help_options():
    parser = argparse.ArgumentParser(description=
    '''Allows to continiously monitor domains for change in subdomains using AWS. Before using, make sure configure your AWS credentials. Example: "aws configure".

    ---Specify domain(s) and discord webhook---
    Example: "python3 shodanmore.py -d test.com -a https://sadsadad"

    ---See if infrastructure deployed---
    Example: "python3 shodanmore.py -s"

    ---Destroying environment---
    Example: "python3 shodanmore.py -n"
    ''',formatter_class=RawTextHelpFormatter)

    parser.add_argument("-d", "--domain", help="Specify domains to monitor", nargs='+')
    #parser.add_argument("-r", "--remove", help="Specify domains to remove") # todo
    parser.add_argument("-a", "--alert", help="Specify discord webhook to sent alerts to")
    parser.add_argument("-s", "--status", help="See if infrastructure is deployed", action='store_true')
    parser.add_argument("-n", "--nuke", help="Destroy environment",action='store_true')

    global args
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit()

def get_targets_bucket_name():
    """
    Retrieves the name of the targets bucket from Terraform output.

    Returns:
        str: The name of the targets bucket.
    """    
    targets_bucket_name = terraform_deployer.run_terraform_command("output", "tf-shodanmore-statefile-temp", "eu-west-1", no_vars=True)
    bucket_name = re.search(r'\"(.+)\.s3', targets_bucket_name).group(1)
    return bucket_name

def store_domains(domains):
    """
    Stores the specified domains in the targets file and uploads it to S3.

    Args:
        domains (list): The list of domains to store.
    """    
    domain_list = domains[0].split(',')
    with open("targets.txt", "w") as outfile: 
        outfile.write('\n'.join(domain_list) + '\n')
    bucket_name = get_targets_bucket_name()
    s3 = boto3.client('s3') 
    s3.upload_file("targets.txt", bucket_name,"targets.txt")

def is_infrastructure_up():
    """
    Checks if the infrastructure is deployed by attempting to head the targets bucket.

    Returns:
        bool: True if the infrastructure is deployed, False otherwise.
    """     
    bucket_name = get_targets_bucket_name()
    try:
        s3 = boto3.client('s3') 
        s3.head_bucket(Bucket=bucket_name)
        print("Infrastructure was found! Proceeding...")
        return True
    except:
        print("Infrastructure is not deployed. python3 shodanmore.py -d test.com -a <web hook>")
        return False

def get_targets_file_contents():
    """
    Retrieves the contents of the targets file from the targets bucket.

    Returns:
        str: The contents of the targets file.
    """    
    bucket_name = get_targets_bucket_name()
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=bucket_name, Key="targets.txt")
    contents = response['Body'].read().decode()
    return contents

def remove_running_tasks(): 
    """
    Stops all running tasks in the ECS cluster.
    """    
    ecs = boto3.client('ecs',region_name="eu-west-1")
    cluster_name = 'tf_domain_enumerator'
    response = ecs.list_tasks(cluster=cluster_name)
    task_arns = response['taskArns'] 
    for task_arn in task_arns:
        ecs.stop_task(cluster=cluster_name, task=task_arn)
        print(f'Stopped task {task_arn}')

def confirm_action():
    """
    Asks for user confirmation for the specified action.

    Returns:
        bool: True if the user confirms, False otherwise.
    """    
    while True:
        response = input("Are you sure you want to proceed? (y/n): ")
        if response.lower() == "y":
            return True
        elif response.lower() == "n":
            return False
        else:
            print("Invalid response. Please enter 'y' to confirm or 'n' to deny.")

# Update later
def get_statistics(bucket_name):
    """
    Retrieves the statistics for the infrastructure.

    Args:
        bucket_name (str): The name of results bucket

    Returns:
        tuple: A tuple containing the creation date and the count of alive domains.
    """    
    s3 = boto3.client('s3')
    file_name = f"{datetime.now().strftime('%Y-%m-%d')}_domains.txt"
    try:    
        response = s3.head_bucket(Bucket=bucket_name)
        creation_date = response['ResponseMetadata']['HTTPHeaders']['date']
        response = s3.get_object(Bucket=bucket_name, Key=file_name)
        content = response['Body'].read().decode()
        domains = content.splitlines()
        alive_domains_count = len(domains)

        return creation_date, alive_domains_count
    except Exception as err:
        print(f"ERROR: error while retrieving statistics {str(err)}")
        raise err

def main():
    help_options()
    if args.domain and args.alert:
        if is_infrastructure_up():
            store_domains(args.domain)
            variables = {
                "dc_webhook_url": args.alert
            }
            terraform_deployer.run_terraform_command("apply -auto-approve", "tf-shodanmore-statefile-temp", "eu-west-1", variables)
            print(f"Starting to monitor: {args.domain}")
    elif args.status:
        if is_infrastructure_up(): #make what's below into function as there is repeating code
            creation_date, alive_domains_count = get_statistics(get_targets_bucket_name())
            print(
                f"""
                Monitored domains: {get_targets_file_contents()}
                Monitoring since: {creation_date}
                Current alive subdomains found: {alive_domains_count}
                """
            )
            
    elif args.nuke:
        if is_infrastructure_up():
            if confirm_action():
                print("Destroying environment...")
                terraform_deployer.run_terraform_command("destroy -auto-approve", "tf-shodanmore-statefile-temp", "eu-west-1")
    else:
        print("The following both arguments are required: -d/--domain,  -a/--alert.")

if __name__ == "__main__":
    main()
