"""
Lambda that retrieves domains found by ECS tools, 
check if they are alive and saves the domains and IPs in S3
"""

from botocore.exceptions import ClientError
import boto3
from datetime import datetime
import json
import requests
from requests.exceptions import ConnectionError, Timeout
import urllib3.exceptions
import socket 
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
import re
import os


def get_log_streams(log_group_name):
    """
    Gets today's log streams from the specified log group.

    Args:
        log_group_name (str): The name of the log group.

    Returns:
        list: The list of log stream names for today.
    """
    try:
        logs_client = boto3.client('logs')
        today = datetime.now().date()
        streams = logs_client.describe_log_streams(logGroupName=log_group_name, orderBy='LastEventTime', descending=True)['logStreams']

        today_streams = []
        for stream in streams:
            if 'lastEventTimestamp' not in stream:
                continue
            else:
                if datetime.fromtimestamp(stream['lastEventTimestamp'] / 1000).date() == today:
                    today_streams.append(stream['logStreamName'])

        return today_streams
    except ClientError as err:
        print(f"ERROR: error occurred while getting log streams: {err}")
        return []
    
def get_domains(log_group_name):
    """
    Gets the list of domains from the log streams in the specified log group.

    Args:
        log_group_name (str): The name of the log group.

    Returns:
        list: The list of unique domains found in the log streams.
    """
    try:   
        streams = get_log_streams(log_group_name)
        unique_domains = []
        logs_client = boto3.client('logs')
        for stream in streams:
            response = logs_client.get_log_events(
                logGroupName=log_group_name,
                logStreamName=stream
            )

            for event in response['events']:
                message = json.loads(event['message'])
                unique_domains.append(message['host'])
        return unique_domains
    except ClientError as e:
        print(f"ERROR: error occurred while getting domains from log streams: {e}")
        return []
    
def resolve_ips(domain):
    """
    Resolves the IP address of the given domain.

    Args:
        domain (str): The domain to resolve.

    Returns:
        str: The resolved IP address, or None if resolution fails.
    """
    try:
        ip = socket.gethostbyname(domain)
        return ip
    except (socket.gaierror, socket.timeout, urllib3.exceptions.ReadTimeoutError):
        pass
    

def check_if_alive(domain):
    """
    Checks if the domain is alive by sending a head request with a timeout of 3 seconds.

    Args:
        domain (str): The domain to check.

    Returns:
        tuple: A tuple containing the domain and its resolved IP address, or None if not alive.
    """
    def get_domains_ips():
        return (domain, resolve_ips(domain))

    try:
        response = requests.head(f'https://{domain}', timeout=3)
    except (ConnectionError):
        try:
            response = requests.head(f'http://{domain}', timeout=3)
        except (ConnectionError):
            pass
        else:
            #print(f'Domain http://{domain} [+++]')
            return get_domains_ips()
    except (urllib3.exceptions.ReadTimeoutError, Timeout):
        return
    else:
        #print(f'Domain https://{domain} [+++]')
        return get_domains_ips()

def upload_to_s3(bucket_name, filename, data):
    """
    Uploads the data to S3 bucket with the specified filename.

    Args:
        bucket_name (str): The name of the S3 bucket.
        filename (str): The filename to use for the uploaded file.
        data (list): The data to upload as lines in the file.
    """
    try:
        s3_client = boto3.client('s3')
        s3_client.put_object(
            Body="\n".join(data),
            Bucket=bucket_name,
            Key=filename
        )
    except ClientError as err:
        print(f"ERROR: error occurred while uploading to S3: {err}")


def lambda_handler(event, context):
    try:
        alive_domains = []
        ips = []
        sub_domains = get_domains("/ecs/domain_enumerator")
        with ThreadPoolExecutor() as executor:
            future_list = [executor.submit(check_if_alive, domain) for domain in sub_domains]
            for future in as_completed(future_list):
                result = future.result()
                if result:
                    domain, ip = result
                    ips.append(ip)
                    alive_domains.append(domain)
            ips = list(dict.fromkeys(ips))            
        domain_file = f"{datetime.now().strftime('%Y-%m-%d')}_domains.txt"
        ip_file = f"{datetime.now().strftime('%Y-%m-%d')}_ips.txt"
        s3_bucket = re.search(r'(.+)\.s3', os.environ['DATA_S3']).group(1)
        upload_to_s3(s3_bucket, domain_file, alive_domains)
        upload_to_s3(s3_bucket, ip_file, ips)  
    except Exception as err:
        print(f"ERROR: error occurred in the lambda_handler: {err}")

#lambda_handler(0,0)
