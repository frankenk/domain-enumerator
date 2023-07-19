import boto3
import sys
import argparse
from argparse import RawTextHelpFormatter
import terraform_deployer
import re
from datetime import datetime
import configparser
import os

# fix code to be readable
class DomainEnumerator:
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.state_bucket_name = ""
        self.region = ""

    def load_configuration(self):
        if not os.path.isfile(self.config_file):
            print(f"ERROR: Configuration file '{self.config_file}' does not exist.")
            exit(1)

        self.config.read(self.config_file)
        self.state_bucket_name = self.config.get('DEFAULT', 'bucket_name')
        self.region = self.config.get('DEFAULT', 'region')

    def help_options(self):
        parser = argparse.ArgumentParser(description=
        '''Allows to continiously monitor domains for change in subdomains using AWS. Before using, make sure configure your AWS credentials. Example: "aws configure".

        ---Specify domain(s) and discord webhook---
        Example: "python3 shodanmore.py -d test.com, test2.com -a https://sadsadad"

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

        self.args = parser.parse_args()

        if len(sys.argv) == 1:
            parser.print_help()
            parser.exit()

    def get_targets_bucket_name(self):
        """
        Retrieves the name of the targets bucket from Terraform output.

        Returns:
            str: The name of the targets bucket.
        """    
        targets_bucket_name = terraform_deployer.run_terraform_command("output", self.state_bucket_name, self.region, no_vars=True)
        bucket_name = re.search(r'\"(.+)\.s3', targets_bucket_name).group(1)
        return bucket_name
    
    def store_domains(self, domains):
        """
        Stores the specified domains in the targets file and uploads it to S3.

        Args:
            domains (list): The list of domains to store.
        """    
        domain_list = domains[0].split(',')
        with open("targets.txt", "w") as outfile: 
            outfile.write('\n'.join(domain_list) + '\n')
        bucket_name = self.get_targets_bucket_name()
        s3 = boto3.client('s3') 
        s3.upload_file("targets.txt", bucket_name,"targets.txt")

    def is_infrastructure_up(self):
        """
        Checks if the infrastructure is deployed by attempting to head the targets bucket.

        Returns:
            bool: True if the infrastructure is deployed, False otherwise.
        """     
        try:
            s3 = boto3.client('s3') 
            s3.head_bucket(Bucket=self.state_bucket_name)
            print("Infrastructure was found! Proceeding...")
            return True
        except:
            print("Infrastructure is not deployed. python3 shodanmore.py -d test.com -a <web hook>")
            return False

    def get_targets_file_contents(self):
        """
        Retrieves the contents of the targets file from the targets bucket.

        Returns:
            str: The contents of the targets file.
        """    
        bucket_name = self.get_targets_bucket_name()
        s3 = boto3.client('s3')
        response = s3.get_object(Bucket=bucket_name, Key="targets.txt")
        contents = response['Body'].read().decode()
        return contents

    def remove_running_tasks(self): 
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

    def confirm_action(self):
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
    def get_statistics(self, bucket_name):
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
            response = s3.list_objects_v2(Bucket=bucket_name)
            
            if 'Contents' in response:
                file_exists = any(file['Key'] == file_name for file in response['Contents'])
                
                if file_exists:
                    response = s3.get_object(Bucket=bucket_name, Key=file_name)
                    content = response['Body'].read().decode()
                    domains = content.splitlines()
                    alive_domains_count = len(domains)
                    
                    return creation_date, alive_domains_count

            return creation_date, 0
        except Exception as err:
            print(f"ERROR: error while retrieving statistics {str(err)}")
            raise err

    def run_enumerator(self):
        self.load_configuration()
        self.help_options()
        variables = {
            "dc_webhook_url": self.args.alert
        } 
        if self.args.domain and self.args.alert:           
            output = terraform_deployer.run_terraform_command("apply -auto-approve", self.state_bucket_name, self.region, variables)
            print(output)
            self.store_domains(self.args.domain)
            print(f"Starting to monitor: {self.args.domain}")
        elif self.args.status:
            if self.is_infrastructure_up():
                creation_date, alive_domains_count = self.get_statistics(self.get_targets_bucket_name())
                print(
                    f"""
                    Monitored domains: {self.get_targets_file_contents()}
                    Monitoring since: {creation_date}
                    Current alive subdomains found: {alive_domains_count}
                    """
                )
                
        elif self.args.nuke:
            if self.is_infrastructure_up():
                if self.confirm_action():
                    print("Destroying environment...")
                    output = terraform_deployer.run_terraform_command("destroy -auto-approve -input=false", self.state_bucket_name, self.region, variables)
                    print(output)
                    print("Successfully destroyed environment")
        else:
            print("The following both arguments are required: -d/--domain,  -a/--alert.")

if __name__ == "__main__":
    app = DomainEnumerator("config.conf")
    app.run_enumerator()
