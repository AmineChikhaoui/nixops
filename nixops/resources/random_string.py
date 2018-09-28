# -*- coding: utf-8 -*-

import nixops.util

class RandomDefinition(nixops.resources.ResourceDefinition):
    """Definition of a random string resource"""

    @classmethod
    def get_type(cls):
        return "random-string"

    @classmethod
    def get_resource_type(cls):
        return "randomStrings"

    def show_type(self):
        return "random-string"

class RandomState(nixops.resources.ResourceState):
    """State of the randomly generated string"""

    state = nixops.util.attr_property("state", nixops.resources.ResourceState.MISSING, int)
    length = nixops.util.attr_property("length", None)
    generated_string = nixops.util.attr_property("generatedString", None)

    @classmethod
    def get_type(cls):
        return "random-string"

    def show_type(self):
        return "random-string"

    def create(self, defn, check, allow_reboot, allow_recreate):
        if self.state == self.MISSING:
            self.log("generating a random string of length {}".format(defn.config["length"]))
            self.generated_string = nixops.util.generate_random_string(length=defn.config["length"])
            self.state = self.UP

    def destroy(self, wipe=False):
        if self.state == self.UP:
            self.generated_string = None
        return True
