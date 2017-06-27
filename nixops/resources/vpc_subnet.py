# -*- coding: utf-8 -*-

# Automatic provisioning of AWS VPC subnets.

import boto3
import botocore

import nixops.util
import nixops.resources
import nixops.resources.ec2_common
import nixops.ec2_utils
from nixops.diff import Diff, Handler
from nixops.state import StateDict

class VPCSubnetDefinition(nixops.resources.ResourceDefinition):
    """Definition of a VPC subnet."""

    @classmethod
    def get_type(cls):
        return "vpc-subnet"

    @classmethod
    def get_resource_type(cls):
        return "vpcSubnets"

    def show_type(self):
        return "{0}".format(self.get_type())


class VPCSubnetState(nixops.resources.ResourceState, nixops.resources.ec2_common.EC2CommonState):
    """State of a VPC subnet."""

    state = nixops.util.attr_property("state", nixops.resources.ResourceState.MISSING, int)
    access_key_id = nixops.util.attr_property("accessKeyId", None)

    @classmethod
    def get_type(cls):
        return "vpc-subnet"

    def __init__(self, depl, name, id):
        nixops.resources.ResourceState.__init__(self, depl, name, id)
        self._client = None
        self._state = StateDict(depl, id)
        self._config = None
        self.subnet_id = self._state.get('subnetId', None)
        self.zone = self._state.get('zone', None)
        self.handle_create_subnet = Handler(['region', 'zone', 'cidrBlock', 'vpcId'])
        self.handle_map_public_ip_on_launch = Handler(['mapPublicIpOnLaunch'],
                                                      after=[self.handle_create_subnet])
        self.handle_create_subnet.handle = self.realize_create_subnet
        self.handle_map_public_ip_on_launch.handle = self.realize_map_public_ip_on_launch

    def show_type(self):
        s = super(VPCSubnetState, self).show_type()
        if self.zone: s = "{0} [{1}]".format(s, self.zone)
        return s

    def get_handlers(self):
        return [getattr(self, h) for h in dir(self) if isinstance(getattr(self, h), Handler)]

    @property
    def resource_id(self):
        return self.subnet_id

    def prefix_definition(self, attr):
        return {('resources', 'vpcSubnets'): attr}

    def get_physical_spec(self):
        return {'subnetId': self.subnet_id}

    def get_definition_prefix(self):
        return "resources.vpcSubnets."

    def connect(self):
        if self._client:
            return
        assert self._state['region']
        (access_key_id, secret_access_key) = nixops.ec2_utils.fetch_aws_secret_key(self.access_key_id)
        self._client = boto3.client('ec2', region_name=self._state['region'],
                                    aws_access_key_id=access_key_id,
                                    aws_secret_access_key=secret_access_key)

    def create_after(self, resources, defn):
        return {r for r in resources if
                isinstance(r, nixops.resources.vpc.VPCState)}

    def create(self, defn, check, allow_reboot, allow_recreate):
        self._config = defn.config
        self.allow_recreate = allow_recreate

        diff_engine = Diff(depl=self.depl, logger=self.logger, config=defn.config,
                           state=self._state, res_type=self.get_type())
        diff_engine.set_reserved_keys(['subnetId', 'accessKeyId', 'tags', 'ec2.tags'])
        diff_engine.set_handlers(self.get_handlers())
        change_sequence = diff_engine.plan()

        self.access_key_id = defn.config['accessKeyId'] or nixops.ec2_utils.get_access_key_id()
        if not self.access_key_id:
            raise Exception("please set 'accessKeyId', $EC2_ACCESS_KEY or $AWS_ACCESS_KEY_ID")

        self._state['region'] = self._config['region']
        self.connect()

        for h in change_sequence:
            h.handle()

        def tag_updater(tags):
            self._client.create_tags(Resources=[self.subnet_id],
                                     Tags=[{"Key": k, "Value": tags[k]} for k in tags])

        self.update_tags_using(tag_updater, user_tags=defn.config["tags"], check=check)

    def realize_create_subnet(self):
        if self.state == self.UP:
            if not self.allow_recreate:
                raise Exception("subnet {} definition changed and it needs to be recreated"
                                " use --allow-recreate if you want to create a new one".format(
                                    self.subnet_id))
            self.warn("subnet definition changed, recreating...")
            self._destroy()
            self._client = None

        self._state['region'] = self._config['region']
        self.connect()

        vpc_id = self._config['vpcId']

        if vpc_id.startswith("res-"):
            res = self.depl.get_typed_resource(vpc_id[4:].split(".")[0], "vpc")
            vpc_id = res._state['vpcId']

        zone = self._config['zone'] if self._config['zone'] else ''
        self.log("creating subnet in vpc {0}".format(vpc_id))
        response = self._client.create_subnet(VpcId=vpc_id, CidrBlock=self._config['cidrBlock'],
                                              AvailabilityZone=zone)
        subnet = response.get('Subnet')
        self.subnet_id = subnet.get('SubnetId')
        self.zone = subnet.get('AvailabilityZone')

        with self.depl._db:
            self.state = self.UP
            self._state['subnetId'] = self.subnet_id
            self._state['cidrBlock'] = self._config['cidrBlock']
            self._state['zone'] = self.zone
            self._state['vpcId'] = vpc_id
            self._state['region'] = self._config['region']

    def realize_map_public_ip_on_launch(self):
        self.connect()
        self._client.modify_subnet_attribute(
            MapPublicIpOnLaunch={'Value':self._config['mapPublicIpOnLaunch']},
            SubnetId=self.subnet_id)

        with self.depl._db:
            self._state['mapPublicIpOnLaunch'] = self._config['mapPublicIpOnLaunch']

    def _destroy(self):
        if self.state != self.UP:
            return
        self.log("deleting subnet {0}".format(self.subnet_id))
        self.connect()
        self._client.delete_subnet(SubnetId=self.subnet_id)
        with self.depl._db:
            self.state = self.MISSING
            self._state['subnetID'] = None
            self._state['region'] = None
            self._state['vpcId'] = None
            self._state['cidrBlock'] = None
            self._state['zone'] = None
            self._state['mapPublicIpOnLaunch'] = None

    def destroy(self, wipe=False):
        self._destroy()
        return True