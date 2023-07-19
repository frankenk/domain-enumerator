"""
Does alerting by sending data to discord webhook.
"""
import json
import requests
import boto3
from botocore.exceptions import ClientError
import os

# On every alert it will lookup, fix
def lookup_topic_arn(topic_name):
    """
    Looks for the topic ARN associated with the specified topic name.

    Args:
        topic_name (str): The name of the topic to lookup.

    Returns:
        str: The ARN of the matching topic, or None if not found.
    """
    try:
        sns = boto3.client("sns")
        response = sns.list_topics()
        for topic in response["Topics"]:
            topic_arn = topic["TopicArn"]
            if topic_arn.endswith(f":{topic_name}"):
                return topic_arn
    except ClientError as err:
        print(f"ERROR: error occurred while looking up the topic ARN: {err}")
    return None


def email_alert(message, topic_arn):
    """
    Sends an email alert using the specified topic ARN.

    Args:
        message (str): The email message to send.
        topic_arn (str): The ARN of the SNS topic for email alerts.
    """
    try:
        sns = boto3.client("sns")        
        sns.publish(TopicArn=topic_arn, Message=message, Subject="Alert")
        print("INFO Email sent")
    except ClientError as err:
        print(f"ERROR: error occurred while sending the email alert: {err}")


def post_discord(url, data):
    """
    Posts the alert message to a Discord webhook URL.

    Args:
        webhook_url (str): The URL of the Discord webhook.
        data (dict): The alert data containing action, message, and alert_type.
    """
    webhook_message = {
        "content": f'{data["action"]},{data["message"]}',
    }
    result = requests.post(url, json=webhook_message)
    if 200 <= result.status_code < 300:
        print(f"INFO sent {result.status_code}")
    else:
        print(f"ERROR not sent with {result.status_code}, response: {result.json()}")


def lambda_handler(event, context):
    """
    Lambda handler function to handle the incoming event.
    """
    data = event
    if data["alert_type"] == "email":
        topic_arn = lookup_topic_arn("tf_shodanmore_email_notifcation")
        email_alert(data["message"], topic_arn)
    elif data["alert_type"] == "discord":
        post_discord(os.environ['DC_WEBHOOK_URL'], data)
    else:
        print("ERROR: invalid alert_type")

#Test using this:
#json_data = '{"action": "new", "message": ["dev.com", "secret.com"], "alert_type": "discord"}'
