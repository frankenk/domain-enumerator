import boto3
import datetime
import re
import os
import json

s3 = boto3.client('s3')

def get_domain_list(date,bucket_name):
    """
    Retrieves the domain list from the S3 bucket for the given date.

    Args:
        date (datetime.date): The date for which to retrieve the domain list.
        bucket_name (str): The name of the S3 bucket.

    Returns:
        list: The domain list for the given date.
    """
    list_key = date.strftime("%Y-%m-%d") + '_domains.txt'

    try:
        response = s3.get_object(Bucket=bucket_name, Key=list_key)
        domain_list = response['Body'].read().decode().splitlines()
        return domain_list
    except s3.exceptions.NoSuchKey:
        return []

def send_data_to_lambda(data):
    """
    Invokes alerting lambda to send notifications
    """    
    client = boto3.client('lambda')
    try:
        response = client.invoke(
            FunctionName='tf_alerting_lambda',
            InvocationType='Event',
            Payload=json.dumps(data).encode()
        )
    except Exception as err:
        print(f"ERROR: Failed to invoke the alerting lambda: {str(err)}")


def compare_domain_lists(previous_list, current_list):
    """
    Compares the previous day's domain list with the current day's domain list
    and reports any removed or new domains.

    Args:
        previous_list (list): The domain list from the previous day.
        current_list (list): The domain list from the current day.
    """
    def format_message(action, domains):
        message = {
            "action": action,
            "message": list(domains),
            "alert_type": "discord"
        }
        return message

    #removed_domains = set(previous_list) - set(current_list)
    new_domains = set(current_list) - set(previous_list)
    
    # if removed_domains:
    #     json_data = format_message("removed",removed_domains)
    #     send_data_to_lambda(json_data)
    #     print(json.dumps(json_data))
    if new_domains:
        json_data = format_message("new",new_domains)
        send_data_to_lambda(json_data)
        print(json.dumps(json_data))

def lambda_handler(event, context):
    """
    AWS Lambda handler function that compares domain lists for the current
    day and the previous day.
    """
    s3_bucket = re.search(r'(.+)\.s3', os.environ['DATA_S3']).group(1)
    today = datetime.date.today()
    previous_day = today - datetime.timedelta(days=1)

    previous_list = get_domain_list(previous_day, s3_bucket)
    current_list = get_domain_list(today, s3_bucket)
    compare_domain_lists(previous_list, current_list)

#lambda_handler(0, 0)
