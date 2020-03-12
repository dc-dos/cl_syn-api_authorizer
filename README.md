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

Complete installtion by installing the encryption
tools. This needs to be installed in the project as
opposed to the P3 site packages to facilitate the
distrubution build.

```bash
 (P3) $> pip install pycryptodome -t .
```

## Packaging

Again, this needs to be done from a Linux installation.

```bash
$> zip ./lambda.zip ./Crypto/* ./authorizer.py
```
