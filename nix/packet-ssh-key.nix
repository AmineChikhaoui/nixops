{ config, lib, uuid, name, ...}:

with lib;

{
  options = {

    name = mkOption {
      default = "charon-${uuid}-${name}";
      type = types.str;
      description = "Name of the packet ssh key.";
    };

    label = mkOption {
      default = "nixops generated key";
      type = types.str;
      description = ''
        The label of the ssh key.
      '';
    };

  } // (import ./packet-credentials.nix lib);
  
  config._type = "packet-ssh-key";
}
