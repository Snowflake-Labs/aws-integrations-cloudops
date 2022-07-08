<p align="center">
</p>

# Use AWS Service Catalog to automate Snowflake integration with Amazon API GW and AWS Lambda to access Amazon service APIs

1. Snowflake API integrations are Snowflake objects that allow Snowflake to read and write data to Amazon S3. Snowflake storage integrations leverage AWS IAM to access S3. The S3 bucket is referenced by the Snowflake integration from an external (i.e. S3) Snowflake stage object
An API integration object stores information about an HTTPS proxy service, including information about the Cloud platform provider e.g. AWS, AWS role ARN (Amazon Resource Name). 

2. This solution provides an integration design pattern and the building blocks for automating Snowflake access to Aamazon service APIs using AWS Service Catalog. The solution implements an AWS Service Catalog product that automates Snowflake access to Amazon service API using an API GW and Lambda.
	1. The Service Catalog product provisions a Snowflake API integration object, attaches an IAM role to it and creates a Lambda function that calls the required AWS service.

## How it Works

1. Provision a Service Catalog Portfolio with a Service Catalog Product
2. The Snowflake Service Catalog Product takes a) Snowflake Connection information and b) S3 bucketname and prefix as input parameters and uses the *aws-snowflake-apigw-integrationobject.yml* CloudFormation template to create a Snowflake API integration object.
	1. The Snowflake Service Catalog Product can be invoked as many times as needed. Each time it creates a Snowflake API integration object to access an API defined in the create-resources-1.0.zip using input parameters supplied above.
3. The template from 2:
	1. Provisions AWS Secrets Manager to store and retrieve Snowflake connection information
	2. Provisions a Lambda function that uses the Snowflake python connector:
		1. Creates a Snowflake API integration object and obtains the Snowflake generated *AWS_IAM_USER_ARN* and *AWS_EXTERNAL_ID* from the Snowflake integration 
		2. Provisions an AWS IAM role that uses the Snowflake generated IAM Principal and External ID from 1 above
		
	
 
## Solution Design

![](images/snowflake-arch.png)


## Prerequisites

1. Create an S3 bucket for the source files: ***s3-snowflakeintegration-accountId-region***. Replace accountId and region with the AWS Account ID and region of your AWS account. These source files will be copied to a destination S3 bucket specified as one of the parameters of the 2nd CloudFormation template
	1. Edit the CloudFormation template in github folder aws-servicecatalog/apigw-sample/template/aws-snowflake-apigw-integrationobject.yml and in the mapping section update the codebucket to the S3 bucket created above.
	2. Upload the contents of the github folder aws-servicecatalog/apigw-sample to the above S3 bucket. This zip file packages the Snowflake connector as an AWS Lambda layer
	3. After completing the upload the above S3 bucket for source files should contain a create-resources-1.0.zip file which contains sample Lambda code. You should also see the Snowflake Python connector zip file and a template folder containing the two CloudFormation templates. 
2. Create a Snowflake user and role with the ability to create Integrations in your Snowflake account. Below are sample SQL Commands that can be used.
```use role accountadmin;
create or replace role apigw_role;
grant role apigw_role to role sysadmin;
grant create integration on account to role apigw_role;

CREATE OR REPLACE USER apigw_admin PASSWORD = '<password>' 
            LOGIN_NAME = 'apigw_admin' 
            DISPLAY_NAME = 'apigw_admin' 
            DEFAULT_ROLE = "apigw_admin" 
            MUST_CHANGE_PASSWORD = FALSE;
GRANT ROLE apigw_role TO USER apigw_admin;
```
3. Optional - Have an AWS User Group with privliges to create an IAM Role, Create and access AWS Secrets, Create Lambda Functions/Layer, Relevant S3 bucket access and KMS Key creation  

## How to Install

**1-step install**
1. Launch the [aws-snowflake-apigw-servicecatalog](https://github.com/Snowflake-Labs/aws-integrations-cloudops/aws-servicecatalog/apigw-sample/template/aws-snowflake-apigw-servicecatalog.yml) template. The template takes the S3 prerequisites bucket (with source files) as a single parameter.
 	
## Test and Run

1. The Snowflake solution creates a Snowflake Service Catalog Portfolio, a ‘SnowflakeEnduserGroup’ AWS IAM group and provides this IAM group with access to the Portfolio. In order to launch the Snowflake Service Catalog Product, you have 2 options – 
	1. Option 1 - Grant your current logged in AWS IAM user/role permissions to access the Snowflake Service Catalog Portfolio by following steps [here](https://docs.aws.amazon.com/servicecatalog/latest/adminguide/getstarted-deploy.html) and launch the Snowflake Service Catalog product using your current logged in IAM user/role.
	2. Option 2 – Add an IAM user to the ‘SnowflakeEnduserGroup’ IAM group. Log in as this IAM user to launch the Snowflake Service Catalog Product
2. Make sure the user that accesses Service Catalog also has access to the User Group or Privilges outlined in the Prerequisites 
3. Navigate to the Service Catalog Console and launch the Snowflake Service Catalog Product.
	1. Provide Snowflake connection details (note that the Snowflake Account ID is the [Account Identifier](https://docs.snowflake.com/en/user-guide/admin-account-identifier.html)), the name of the Storage Integraiton in Snowflake, the S3 bucket created in the prerequisites with the code and the S3 bucket name for the data bucket 
5. From your Snowflake account (snowsql or console)-
	1. Validate that a new Snowflake API integration object has been created - the name of the integration object will be the input paramater in the step above and *_<SUFFIX>* appended to it (DESC INTEGRATION *'integrationobjectname'*). You can sort the output by date to identify the latest object created.
	2. Obtain the *AWS_IAM_USER_ARN* and *AWS_EXTERNAL_ID* parameters from above and check that the AWS IAM role uses those as the trust relationship and external id parameters
	3. Validate that a new external function has been created in Snowflake with this command by providing values for Snowflake database, schema, suffix used: DESCRIBE FUNCTION <database>.<schema>.AWS_AUTOPILOT_CREATE_MODEL_<SUFFIX>(VARCHAR, VARCHAR, VARCHAR);   
	4. The sample create-resources-1.0.zip contains the code for the 'create_model' API call to Amazon SageMaker AutoPilot. You should be able to run the following SQL to invoke this API call : 
			SELECT <database>.<schema>.AWS_AUTOPILOT_CREATE_MODEL_<suffix>('model-name','ABALONE', 'RINGS');   where ABALONE is the table name and RINGS is the column to be predicted.Please see: https://archive.ics.uci.edu/ml/datasets/abalone

## References
You can find the full implementation of the Amazon SageMaker integration with Snowflake here: https://github.com/aws-samples/amazon-sagemaker-integration-with-snowflake/blob/main/snowflake-integration-overview.md


## Cleanup

To clean up your account after deploying the solution perform the following steps:

1.	Terminate the Snowflake Service Catalog Provisioned Product. Follow steps [here](https://docs.aws.amazon.com/servicecatalog/latest/userguide/enduser-delete.html) to terminate Service Catalog provisioned products
2.	If you followed Step 1a (Option 1) in the Test and Run section then remove the access of your logged in AWS user from the Snowflake Service Catalog Portfolio. If you followed Step 1b (Option 2) in the Test and Run section, then remove the IAM user from the ‘SnowflakeEnduserGroup’ IAM group
3.	Delete the CloudFormation stack for the aws-snowflake-apigw-servicecatalog template


 
