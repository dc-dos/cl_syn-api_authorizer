# Building the SSI API Authorizer Lambda

The SSI API Authorizer was developed in Python 3.6.5. Use of a Python Virtual Environment is recommended for developement. 

NOTE: This is code for an AWS Lambda function. To properly run the distribution, it must be packaged on a linux box due to binary parts of the crypto packages.

## Download and Install

Download from git (proper creds required):

```bash
 $> git clone <https://github.com/dc-dos/cl_syn-api_authorizer.git>

```

## Create and Activate Virtual Environment

```bash
 $> python3 -m venv ./P3
 $> source P3/bin/activate
```

## Dependencies

Complete installtion by installing the AWS client
library needed for the DynamoDB interface.

```bash 
 (P3) $> pip install boto3 -t .
```

## Packaging

Pure Python 3 at this point so building on any platform works

```bash
$> zip ./auth_lambda.zip ./boto3/*.* ./authorizer.py
$> zip ./proxy_lambda.zip ./worxproxy.py
```

## API Usage

Everything operates on one Authorizer lambda and one WorxProxy lambda. 

 1. The Authorizer examines the AuthorizationHeader to reveal the customer key that 
    is then used to lookup their auth record in the DynamoDB table. If the Method and 
    Endpoint are validated for the key, the access is granted. All errors or any other
    outcome result in denial of access.
 2. The WorxProxy transforms the request sent in REST format to a Worx Action based request
    and that request is sent to the designated *worx server and the response returned to the 
    user in a JSON Format (via API Gateway) consisting of an HTTP response code and results of
    the Worx call in json format.

    The transformation from REST to Worx and back conforms to the following patterns:

    - The REST Path is parsed into nodes to be used in constructing the name of the Java class.
    - All Querystring is parsed and combined with the JSON.API (see Examples below) body of the
      REST call (if any) for a unified parameter collection that is re-encoded as a Querystring for 
      GETs and as a www-urlencoded-form for POSTs and PUTs. 
    - For REST POST calls, Action will be path nodes joined by 'dots' with '.Create' appended. 
    - For REST GET calls, Action will be path nodes joined by 'dots' with last node capitalized.
    - For REST PUT calls, Action will be path nodes joined by 'dots' with last node capitalized.
    - All Worx API call return values are wrapped into a JSON-API return formats and send back to 
      the REST call originator (see Examples below).

    **Examples**

    