import boto3
import logging

ubuntu_ami_id = "ami-c7e0c82c"
instance_type = "t2.micro"
vpn_tag_name = "vpn_status"
LOG = logging.getLogger("Ec2Helper")


class Ec2Helper:
    def __init__(self, check_free_tier_rules=True):
        self.check_free_tier_rules = check_free_tier_rules
        self.ec2 = boto3.resource('ec2')
        self.client = boto3.client('ec2')

    def create_instance(self):
        if self._check_active_instance_exist():
            LOG.info("Found instances. Clearing")
            self.clear_instances()
        created_instances = self.ec2.create_instances(
            ImageId=ubuntu_ami_id, InstanceType=instance_type,
            MinCount=1, MaxCount=1)
        instances_ids = list()
        for instance in created_instances:
            instances_ids.append(instance.id)
        LOG.info("Instance %s created. Wait for instance is running",
                 instances_ids[0])
        waiter = self.client.get_waiter('instance_running')
        waiter.wait(InstanceIds=instances_ids)
        LOG.info("Instance %s is running", instances_ids[0])
        self._add_vpn_tag_to_instance(instances_ids[0], "created")
        return instances_ids

    def start_instance(self):
        pass

    def stop_instance(self):
        pass

    def terminate_instance(self, instance_id):
        ids = list([instance_id])
        LOG.info("Terminating instance %s started", instance_id)
        self.ec2.instances.filter(InstanceIds=ids).terminate()
        waiter = self.client.get_waiter('instance_terminated')
        LOG.info("Waiting for terminating instance %s is complete", instance_id)
        waiter.wait(InstanceIds=[instance_id])
        LOG.info("Instance %s terminated", instance_id)

    def clear_instances(self):
        LOG.info("Terminating all instances")
        instances = self.list_instances()
        for instance in instances:
            self.terminate_instance(instance.id)

    def list_instances(self):
        instances = self.ec2.instances.filter(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
        return instances

    def _check_active_instance_exist(self):
        return sum(1 for _ in self.list_instances()) != 0

    def _add_vpn_tag_to_instance(self, instance_id, tag):
        self.ec2.create_tags(Resources=[instance_id],
                             Tags=[{'Key': vpn_tag_name,
                                    'Value': tag}])

    def check_active_instance(self):
        instances = self.ec2.instances.filter(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']},
                     {'Name': 'tag:' + vpn_tag_name,
                      'Values': ['active']}])
        ids = [instance.id for instance in instances]
        if len(ids) > 0:
            return ids[0]
        else:
            return None
