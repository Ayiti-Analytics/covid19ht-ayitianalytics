import boto3
from botocore.exceptions import ClientError
import sys
import requests
import re
import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import datetime




def update_db_with_ip(access_key, secret_access_key, rule_description,security_group_id,ip_address = None, port = 5432):
    ec2 = boto3.client('ec2',
                       region_name = 'us-east-2',
                       aws_access_key_id = access_key,
                       aws_secret_access_key = secret_access_key)
    # Get current IP address
    if ip_address is None:
        ip_data = requests.get('https://ifconfig.me/ip')
        ip_text = ip_data.text
    else:
        ip_text = ip_address
    try:
        if re.match(r'\d{3}\.\d{2}\.\d{3}.\d{3}',ip_text):
            pass
        else:
            raise
    except:
        print("Unexpected error:", sys.exc_info()[0])
        raise
    
    try:
        response = ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    'FromPort': 5432,
                    'IpProtocol': 'tcp',
                    'IpRanges': [
                        {
                            'CidrIp': ip_text+'/32',
                            'Description': rule_description,
                        },
                    ],
                    'ToPort': 5432,
                },
            ],
        )

        print(response)
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "InvalidPermission.Duplicate":
            # ignore the target exception
            print(f"{ip_address} already open to {port}")
            pass
        else:
            print(e.response["Error"]["Code"])
            raise(e)
    except:
        print("Unexpected error:", sys.exc_info()[0])
        raise
        
def get_posgres_connection():
    load_dotenv()
    access_key = os.getenv("AWS_ACCESS_KEY")
    secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    username = os.getenv("username")
    security_group_id = os.getenv("AWS_SECURITY_GROUP")
    ip_update_descrition = f"{username} -{datetime.date.today()}"
    
    update_db_with_ip(access_key,secret_access_key,ip_update_descrition,security_group_id)
    
    db_name = os.getenv("PSQL_DB_NAME")
    db_user = os.getenv("PSQL_DB_USER")
    db_password = os.getenv("PSQL_DB_PASSWORD")
    db_host = os.getenv("PSQL_DB_HOST")
    sql_engine = create_engine(f'postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}')
    return sql_engine