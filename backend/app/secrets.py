import boto3


def read_secret(parameter_name: str, region: str) -> str:
    response = boto3.client("ssm", region_name=region).get_parameter(
        Name=parameter_name, WithDecryption=True
    )
    parameter = response["Parameter"]
    if parameter["Type"] != "SecureString" or not parameter["Value"]:
        raise RuntimeError("Runtime secrets require non-empty SSM SecureString parameters.")
    return parameter["Value"]
