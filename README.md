# domain-enumerator

Personal project to learn terraform and get little bit better at AWS. If you're going to run this, always review the code before running.

Basically a subdomain enumerator that:
1. Periodically runs one or more enumeration tools (e.g. subfinder) in ECS against targets
2. Saves alive subdomains to S3
3. Compares changes in subdomain number and sends alerts to Discord webhook if new domains appear.    

![[images/domain_enumerator.drawio.png]]

## Requirements

Assumes that AWS credentials were setup using `aws configure`. Uses Docker to run terraform in container. Requires Python docker SDK and boto3 libraries. 

Install requirements by running `pip install -r requirements.txt`.

## Usage

Edit `config.conf` and specify your region and bucket that will store Terraform statefile. 
```
[DEFAULT]
bucket_name = tf-domain-enumerator-default-statefile
region = eu-west-1
```

Deploying the infrastructure:
- `python3 domain_enumerator.py -d example.com -a https://weebhook`

Seeing status of monitoring (just prints monitored domains and uptime):
- `python3 domain_enumerator.py -s`

Destroying environment
- `python3 shodanmore.py -n`

To add different or more domains just specify them with `-d` flag (will overwrite previous ones):
- `python3 domain_enumerator.py -d example.com, tesla.com -a https://weebhook`

## Billing

Costs should be minimal or non-existant (if you're on free plan) as it runs ECS only every several hours for 10-20 s.  