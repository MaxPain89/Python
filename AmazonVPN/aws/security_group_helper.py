import boto3
import logging

from botocore.exceptions import ClientError

VpnSecurityGroupName = 'VPN_SG'
LOG = logging.getLogger("SecurityGroupHelper")


class SecurityGroupHelper:
    def __init__(self):
        self.ec2 = boto3.resource('ec2')
        self.client = boto3.client('ec2')

    def create_security_group_if_not_exist(self):
        existed = self._check_existing_sg()
        if existed:
            LOG.info("Found existed security group %s", existed)
            return existed
        LOG.info("Didn't find security group. Creating...")
        security_group = self.ec2.create_security_group(
          Description='SG for vpn instance',
          GroupName=VpnSecurityGroupName,
          # VpcId='string'
        )
        self.client.authorize_security_group_ingress(
            GroupId=security_group.id,
            IpPermissions=[
                {'IpProtocol': 'udp',
                 'FromPort': 1194,
                 'ToPort': 1194,
                 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp',
                 'FromPort': 22,
                 'ToPort': 22,
                 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ])
        LOG.info("Security group %s created", security_group.id)
        return security_group.id

    def _check_existing_sg(self):
        try:
            response = self.client.describe_security_groups(
                GroupNames=[VpnSecurityGroupName])
        except ClientError:
            return None
        group_ids = [group["GroupId"] for group in response['SecurityGroups']]
        if len(group_ids) > 0:
            return group_ids[0]
        else:
            return None
