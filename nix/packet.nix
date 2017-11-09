{ config, lib, ...}:

with lib;
with import ./lib.nix lib;

{
  options = {
    deployment.packet = (import ./packet-credentials.nix lib) // {

      projectId = mkOption {
        type = types.str;
        description = ''
          The id of the project where the device will be created.
        '';
      };

      hostname = mkOption {
        default = "packet-nixops";
        type = types.str;
        description = ''
          The hostname of the Packet machine.
        '';
      };

      facility = mkOption {
        type = types.str;
        description = ''
          The facilily in which the device will be created.
        '';  
      };

      plan = mkOption {
        type = types.str;
        description = ''
          The hardware config plan.
        '';
      };

      billingCycle = mkOption {
        default = "hourly"; #FIXME don't set default, this is just for testing
        type = types.str;
        description = ''
          The billing cycle, can be monthly/hourly.
        '';
      };

      userData = mkOption {
        default = null;
        type = types.nullOr types.str;
        description = ''
          A strig containing the desired user data for the device.
        '';
      };

      spotInstance = mkOption {
        default  = true; #FIXME this is just for testing.
        type = types.bool;
        description = ''
          Whether the device should be a spot instance.
        '';
      };

      spotPriceMax = mkOption {
        default = 1;
        type = types.int;
        description = ''
          Maximum biding price for the spot instance.
        '';
      };

      operatingSystem = mkOption {
        default = "nixos_17_03"; #FIXME add list of Operating Systems to nix/eval-machines-info.nix to allow adding more NixOS versions
        type = types.str;
        description = ''
          Version of NixOS operating system, currently only nixos_17_03 is available.
        '';
      };

      userSSHKeys = mkOption {
        default = [];
        type = types.listOf (types.either types.str (resource "packet-ssh-key"));
        apply = map (x: if builtins.isString x then x else "res-" + x._name);
        description = ''
          Allowed user ssh keys to be added to the root authorized keys.
        '';
      };

    }; 
  };
  
  config = mkIf (config.deployment.targetEnv == "packet") {
    nixpkgs.system = mkOverride 900 "x86_64-linux";
  };
}
