{ config, lib, ...}:

with lib;

{
  options = {
    deployment.packet = (import ./packet-credentials.nix lib "instance") // {
      
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

    }; 
  };
  
  config = mkIf (config.deployment.targetEnv == "packet") {
    nixpkgs.system = mkOverride 900 "x86_64-linux";
  };
}
