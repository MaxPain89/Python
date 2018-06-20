from AmazonVPN.aws.ec2_helper import Ec2Helper
import logging

from AmazonVPN.aws.security_group_helper import SecurityGroupHelper

logging.basicConfig(level=logging.INFO)

helper = Ec2Helper()
# created_instances = helper.create_instance()
# for instance in created_instances:
#     print(instance)
# instances = helper.check_active_instance()
# print(instances)

# create SG
sg_helper = SecurityGroupHelper()
sg = sg_helper.create_security_group_if_not_exist()
# print(sg)
# print(sg_helper._check_existing_sg())
