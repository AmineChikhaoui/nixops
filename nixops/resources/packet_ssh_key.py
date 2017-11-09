import nixops.util
from nixops.resources import ResourceState, ResourceDefinition

import packet

class PacketSSHKeysDefinition(ResourceDefinition):

    @classmethod
    def get_type(cls):
        return "packet-ssh-key"

    @classmethod
    def get_resource_type(cls):
        return "packetSSHKeys"

    def show_type(self):
        return self.get_type()

class PacketSSHKeysState(ResourceState):

    state = nixops.util.attr_property("state", ResourceState.MISSING, int)

    key_id = nixops.util.attr_property("keyId", None)
    auth_token = nixops.util.attr_property("authToken", None)
    label = nixops.util.attr_property("label", None)
    key = nixops.util.attr_property("key", None)
    owner = nixops.util.attr_property("owner", None)
    private_key = nixops.util.attr_property("privateKey", None)
    public_key = nixops.util.attr_property("publicKey", None)

    @classmethod
    def get_type(cls):
        return "packet-ssh-key"

    @property
    def resource_id(self):
        return self.key_id

    def __init__(self, depl, name, id):
        ResourceState.__init__(self, depl, name, id)
        self._client = None

    def get_definition_prefix(self):
        return "resources.packetSSHKeys."

    def get_client(self):
        assert self.auth_token
        if self._client is None:
            self._client = packet.Manager(auth_token=self.auth_token)

        return self._client

    def create(self, defn, check, allow_reboot, allow_recreate):
        self.auth_token = defn.config["authToken"]
        if not self.auth_token:
            raise Exception("please set the option authToken to create the resource")

        if not self.key:
            (private, public) = nixops.util.create_key_pair(type="rsa")
            with self.depl._db:
                self.public_key = public
                self.private_key = private

        if check or self.state != self.UP:
            ssh_key = self.get_ssh_key()
            if not ssh_key:
               self.log("uploading Packet ssh key ...")
               ssh_key = self.get_client().create_ssh_key(
                       label=defn.config["label"],
                       public_key=self.public_key)

               with self.depl._db:
                   self.state = self.UP
                   self.key_id = ssh_key.id
                   self.label = ssh_key.label
                   # As of today the owner id comes in as /users/{user_id}
                   # so we take the relevant part that will be used in
                   # packet devices
                   self.owner = ssh_key.owner.split("/")[2]

    def get_ssh_key(self):
        try:
            if self.key_id:
                ssh_key = self.get_client().get_ssh_key(self.key_id)
            else:
                ssh_key = None
        except Exception as error:
            if error.message == "Error 404: Not Found":
                ssh_key = None
            else:
                raise error
        return ssh_key

    def destroy(self, wipe=False):
        if self.state == self.UP:
            ssh_key = self.get_ssh_key()
            self.log("deleting Packet ssh key {}...".format(self.key_id))
            ssh_key.delete()
            return True
