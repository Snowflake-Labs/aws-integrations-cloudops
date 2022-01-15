# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#  Lambda that creates Snowflake integration object in Snowflake and the corresponding IAM role in AWS
#  - Uses Snowflake Python Connector
#
# @kmmahaj

import json
import urllib
import boto3
import os
import string
import random
import snowflake.connector
import logging
import urllib3
from snowflake.connector import DictCursor

AWS_EXTERNAL_ID = ""
AWS_IAM_USER_ARN = ""

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)
http = urllib3.PoolManager()

session = boto3.session.Session()

sf_config_name = ''
allowed_sf_config = ('snowaccount', 'snowuser', 'snowpass', 'snowdb', 'snowschema')

def get_secret_value(secret_name):
    """
    get secret value from AWS Secrets Manager
    :param secret_name: name of the secret passed
    :return secret_value: value of the secret passed
    """
    client = session.client(service_name='secretsmanager')
    secret_value = ''
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        logger.error(f"error while executing get_secret_value, {e}")
        raise Exception()
    else:
        secret_value = get_secret_value_response['SecretString'] if 'SecretString' in get_secret_value_response else ''
    finally:
        return secret_value


def get_snowflake_config(sf_config_name):
    """
    get snowflake config, throws exception if invalid
    :return config: snowflake config dict
    """
    config = json.loads(get_secret_value(sf_config_name))
    for key in config:
        if not config.get(key, ''):
            logger.error(f"either key {key} do not exist, or non empty value found")
            raise Exception()
    return config


def create_iam_policy(externalid, iamrolearn,SNOW_S3_BUCKET,SNOW_INT,SNOW_ROLE):
    iam = boto3.client('iam')
    s3fullresourcearn = "arn:aws:s3:::" + SNOW_S3_BUCKET + '/*'
    s3bucketresourcearn = "arn:aws:s3:::" + SNOW_S3_BUCKET
    s3prefix = SNOW_S3_BUCKET + '/*'
    s3_access_policy = {
        "Version": "2012-10-17",
        "Statement": [
        {
            "Effect": "Allow",
            "Action": [
              "s3:PutObject",
              "s3:GetObject",
              "s3:GetObjectVersion",
              "s3:DeleteObject",
              "s3:DeleteObjectVersion"
            ],
            "Resource": s3fullresourcearn
        },
        {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": s3bucketresourcearn
        }
        ]
    }
    snowpolicy = "SnowflakeS3AccessPolicy-" + SNOW_S3_BUCKET + SNOW_INT
    response_policy = iam.create_policy(
        PolicyName=snowpolicy,
        PolicyDocument=json.dumps(s3_access_policy)
    )
    
    policyArn = response_policy['Policy']['Arn']

    trust_relationship_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": iamrolearn
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "sts:ExternalId": externalid
                }
            }
        }
    ]
    }
    
    AssumeRolePolicyDocument = json.dumps(trust_relationship_policy)
    print(AssumeRolePolicyDocument)
    
    snowrole = SNOW_ROLE
    response_role = iam.create_role(
        RoleName=snowrole,
        AssumeRolePolicyDocument=AssumeRolePolicyDocument
    )
    print(response_role)
    
    response = iam.attach_role_policy(
        RoleName=snowrole,
        PolicyArn=policyArn
    )

    print(response)


def lambda_handler(event, context):
    
    logger.info('EVENT Received: {}'.format(event))

    CURRENT_AWS_ACCOUNT = os.environ['AWSACCOUNT']
    sf_config_name = os.environ['SNOW_SECRET']
    sf_config = get_snowflake_config(sf_config_name)
    logger.info(f'snowflake config successfully retrieved from secrets')
 
    assert isinstance(sf_config, dict), 'sf_config config must be of type dict'

    ctx = snowflake.connector.connect(
        user=sf_config['snowuser'],
        password=sf_config['snowpass'],
        role='ACCOUNTADMIN',
        account=sf_config['snowaccount'],
        database=sf_config['snowdb'],
        schema=sf_config['snowschema'],
        ocsp_response_cache_filename="/tmp/ocsp_response_cache"
        )
    cs = ctx.cursor()

    SNOW_S3_BUCKET = event['parameterValue']

    letters = string.ascii_lowercase
    randomstr = ''.join(random.choice(letters) for i in range(3))
    randomnum = str(random.randrange(2,100))
    SNOW_INT = "S3INT" + randomstr + randomnum
    SNOW_ROLE = "SFAccessRole-" + SNOW_INT
    
    
    SNOW_S3_LOCATION = 's3://' + SNOW_S3_BUCKET +'/'
    try:
        
        sql_1 = 'create storage integration ' + SNOW_INT  + ' type = external_stage storage_provider = s3 enabled = true' \
                + ' storage_aws_role_arn = ' + "'" + "arn:aws:iam::" + CURRENT_AWS_ACCOUNT + ":role/" + SNOW_ROLE + "'" + ' storage_allowed_locations = (' + "'" + SNOW_S3_LOCATION + "'" +')'
        print(sql_1)
        cs.execute(sql_1)
        
        sql_2 = 'desc integration ' + SNOW_INT
        print(sql_2)
        cs.execute(sql_2)
        
        query_id_desc = cs.sfqid
        
        sql_3 = 'select "property", "property_value" from table(result_scan('  + "'" +  query_id_desc + "'" + '))' + ' where "property" = ' + "'" + "STORAGE_AWS_EXTERNAL_ID" + "'"
        print(sql_3)
        cs.execute(sql_3)
        for (property, property_value) in cs:
            AWS_EXTERNAL_ID = property_value
            print('{0}, {1}'.format(property, AWS_EXTERNAL_ID))
  
        
        sql_4 = 'select "property", "property_value" from table(result_scan('  + "'" +  query_id_desc + "'" + '))' + ' where "property" = ' + "'" + "STORAGE_AWS_IAM_USER_ARN" + "'"
        print(sql_4)
        cs.execute(sql_4)
        for (property, property_value) in cs:
            AWS_IAM_USER_ARN = property_value
            print('{0}, {1}'.format(property, AWS_IAM_USER_ARN))
            
        create_iam_policy(AWS_EXTERNAL_ID,AWS_IAM_USER_ARN,SNOW_S3_BUCKET,SNOW_INT,SNOW_ROLE)
        
        sql_5 = 'create stage ' + "S3STAGE" + SNOW_INT + ' storage_integration = ' + SNOW_INT + ' url = (' + "'" + SNOW_S3_LOCATION + "'" +')'
        print(sql_5)
        cs.execute(sql_5)
        
    finally:
        cs.close()
    ctx.close()

    return 'SUCCESS'
    
