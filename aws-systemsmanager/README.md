<p align="center">
</p>

# Use AWS Systems Manager Automation runbooks to automate Snowflake storage integrations in AWS


## Overview

1. Snowflake storage integrations are Snowflake objects that allow Snowflake to read and write data to Amazon S3. This Control Tower integration with Snowflake solution enables Snowflake storage integrations with Amazon S3 to be automatically available for all newly added AWS accounts in an AWS Control Tower environment.
2. This solution provisions an AWS Systems Manager Automation runbook that automates all the steps required by Snowflake to create a storage integration with S3 in an AWS account.


## How it Works

1. Each time you launch the AWS Systems Manager Automation runbook in your account, it provisions a Snowflake storage integration object, attaches an IAM role to it and creates an external Snowflake stage object for Amazon S3 by leveraging the integration object and your supplied S3 bucket as parameters. The runbook uses AWS Secrets Manager to store and retrieve Snowflake connection information. You can launch the runbook as many times as needed to create new integrations between Snowflake and additional S3 buckets in your account.
2. The AWS Identity and Access Management (IAM) role that is created by the runbook provides trusted access to Snowflake to reference the S3 bucket in your account. The Principal element and external ID in the role's trust policy are extracted by the runbook from the Snowflake integration object.
3. The runbook deployment itself is fully automated using 1-click automation via AWS CloudFormation. The CloudFormation template first takes your Snowflake connection information and stores it in AWS Secrets Manager. It then provisions an AWS Lambda Layer that wraps the Snowflake connector for Python, provisions an AWS Lambda function that that uses the connector to create the Snowflake integration and finally provisions the Systems Manager runbook in your account that leverages this Lambda.

 
## Solution Design

![](images/snowflake-systemsmanager-arch-diagram.PNG)


## Setup

**Prerequisites:**

1. Create an S3 bucket: *s3-snowflakeintegration-accountId-region*. Replace accountId and region with the AWS Account ID and region of your shared services AWS account. 
2. Create a folder called *SnowflakeIntegration_Lambda_SSM* and upload the [SnowflakeIntegration_Lambda_SSM.zip](https://github.com/Snowflake-Labs/aws-integrations-cloudops/blob/master/aws-systemsmanager/lambda/SnowflakeIntegration_Lambda_SSM.zip) file. This lambda uses the Snowflake Python Connector to query and update Snowflake
3. Upload the [snowflakelayer.zip](https://github.com/Snowflake-Labs/aws-integrations-cloudops/blob/master/aws-systemsmanager/layer/snowflakelayer.zip) in the root folder of this S3 bucket. This zip file packages the Snowflake connector as an AWS Lambda layer
	
**Install**

1. 1 step install. Launch the [aws-snowflake-ssm.yml](https://github.com/Snowflake-Labs/aws-integrations-cloudops/blob/master/aws-systemsmanager/cft/aws-snowflake-ssm.yml) template. The template takes connection information for your Snowflake account as parameters.
 	
## Test and Validate

1. Navigate to the AWS Systems Manager console in your AWS account. Select Documents from the left panel and then select the Owned by me tab on the console. Search for the ‘Custom-Snowflakestorageintegration’ document in the search filter. Click on this document and then select Execute automation from the right corner of your console. On the Execute automation document screen, select Simple execution, provide the S3 bucket name in the Input parameters section and click on Execute
2.	Navigate back to the AWS Systems Manager console, select Automation from the left panel from where you can track the execution of your automation runbook on the Automation executions screen to ensure that the status column displays Success.
3. Navigate to the AWS IAM console and check that a new IAM role has been provisioned that ends with *S3INTxxxxx* suffix. This suffix will also be the name of your new Snowflake integration object
4. From your Snowflake account (snowsql or console)-
	1. Validate that a new Snowflake integration object has been created (DESC INTEGRATION *'integrationobjectname'*)
	2. Obtain the *AWS_IAM_USER_ARN* and *AWS_EXTERNAL_ID* parameters from above and check that the AWS IAM role uses those as the trust relationship and external id parameters
	3. Validate that a new storage object has been created in Snowflake that references the S3 bucket and uses the integration object (SHOW STAGES IN ACCOUNT)