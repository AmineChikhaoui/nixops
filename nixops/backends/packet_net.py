import time

from nixops.backends import MachineDefinition, MachineState
import nixops.resources

import packet

class PacketDefinition(MachineDefinition):
    #FIXME mostly boilerplate code, should be factored out/removed at some point
    @classmethod
    def get_type(cls):
        return "packet"

    def show_type(self):
        return self.get_type()

class PacketState(MachineState):

    state = nixops.util.attr_property("state", MachineState.MISSING, int)
    auth_token = nixops.util.attr_property("authToken", None)
    project_id = nixops.util.attr_property("projectId", None)
    hostname = nixops.util.attr_property("hostname", None)
    facility = nixops.util.attr_property("facility", None)
    plan = nixops.util.attr_property("plan", None)
    billing_cycle = nixops.util.attr_property("billingCycle", None)
    user_data = nixops.util.attr_property("userData", None)
    spot_instance = nixops.util.attr_property("spotInstance", False, type=bool)
    spot_price_max = nixops.util.attr_property("spotPriceMax", None, int)
    public_ipv4 = nixops.util.attr_property("publicIpv4", None)
    private_ipv4 = nixops.util.attr_property("privateIpv4", None)
    device_id = nixops.util.attr_property("deviceId", None)
    ssh_keys = nixops.util.attr_property("sshKeys", [], "json")

    @classmethod
    def get_type(cls):
        return "packet"

    def __init__(self, depl, name, id):
        MachineState.__init__(self, depl, name, id)
        self._client = None

    def get_client(self):
        assert self.auth_token
        if self._client is None:
            self._client = packet.Manager(auth_token=self.auth_token)

        return self._client

    def wait_for_instance_up(self, device_id):
        self.log("waiting for IP address... ".format(self.name))

        while True:
            instance = self.get_device()
            if instance is not None:
                self.log_continue("[{0}]".format(instance.state))
                if instance.state not in { "provisioning", "active" }:
                    raise Exception("Packet instance {0} is in an unknown state {1}".format(self.device_id, instance.state))
                if instance.state != "active":
                    time.sleep(3)
                    continue
                else:
                    for ip in instance.ip_addresses:
                        if ip["address_family"] == 4:
                            if ip["public"] == True:
                                self.public_ipv4 = ip["address"]
                            else:
                                self.private_ipv4 = ip["address"]

                    self.state = self.UP
                    break
                self.log_end("{0} / {1}".format(self.public_ipv4, self.private_ipv4))
            else:
                self.reset_state()
                break

    def create_after(self, resources, defn):
        return {r for r in resources if
                isinstance(r, nixops.resources.packet_ssh_key.PacketSSHKeysState)}

    def create(self, defn, check, allow_reboot, allow_recreate):
        config = defn.config["packet"]
        self.auth_token = config["authToken"]
        if not self.auth_token:
            raise Exception("please set deployment.ec2.authToken")

        if not self.device_id:
            self.log("creating Packet instance (facility {0}, plan {1}, billing cycle {2} )".format(
                config["facility"], config["plan"], config["billingCycle"]))

            args = self.process_device_entry(config)
            try:
                response = self.get_client().create_device(**args)
            except Exception as error: #FIXME catch more accurate exceptions
                raise error
            with self.depl._db:
                self.state = self.STARTING
                self.device_id = response.id
                self.facility = config["facility"]
                self.plan = config["plan"]
                self.billing_cycle = config["billingCycle"]
                self.spot_instance = config["spotInstance"]
                self.spot_price_max = config["spotPriceMax"]
                self.operating_system = config["operatingSystem"]
                self.ssh_keys = args["user_ssh_keys"]

            self.wait_for_instance_up(response.id)
        else:
            if self.state == self.STARTING:
                self.wait_for_instance_up(self.device_id)

    def process_device_entry(self, config):
        args = dict()
        args["project_id"] = config["projectId"]
        args["hostname"] = config["hostname"]
        args["plan"] = config["plan"]
        args["facility"] = config["facility"]
        args["operating_system"] = config["operatingSystem"]
        args["spot_instance"] = config["spotInstance"]
        args["spot_price_max"] = config["spotPriceMax"]
        ssh_keys = []
        if len(config["userSSHKeys"]) > 0:
            for key in config["userSSHKeys"]:
                if key.startswith("res-"):
                    res = self.depl.get_typed_resource(key[4:], "packet-ssh-key")
                    key = res.owner
            ssh_keys.append(key)
        args["user_ssh_keys"] = ssh_keys

        return args

    def get_ssh_name(self):
        return self.public_ipv4

    def get_ssh_private_key_file(self):
        for r in self.depl.active_resources.itervalues():
            if isinstance(r, nixops.resources.packet_ssh_key.PacketSSHKeysState) and r.state == nixops.resources.packet_ssh_key.PacketSSHKeysState.UP and r.owner in self.ssh_keys:
                return self.write_ssh_private_key(r.private_key)

    def get_ssh_flags(self, *args, **kwargs):
        file = self.get_ssh_private_key_file()
        super_flags = super(PacketState, self).get_ssh_flags(*args, **kwargs)
        return super_flags + (["-i", file] if file else [])

    def get_device(self):
        try:
            instance = self.get_client().get_device(device_id=self.device_id)
        except Exception as error:
            if error.message == "Error 404: Not found":
                self.warn("machine {} was already deleted".format(self.device_id))
                return None
            else:
                raise error
        return instance

    def reset_state(self):
        with self.depl._db:
            self.state = self.MISSING
            self.device_id = None
            self.public_ipv4 = None
            self.private_ipv4 = None

    def destroy(self, wipe=False):
        if not self.device_id: return True
        if not self.depl.logger.confirm("are you sure you want to destroy Packet machine {0}?".format(self.name)): return False

        self.log_start("destroying Packet machine... ".format(self.name))
        device = self.get_device()
        if device is not None:
            device.delete()

        self.reset_state()
