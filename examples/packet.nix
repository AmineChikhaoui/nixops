{ authToken
, projectId
}:
{
  machine =
    { config, pkgs, lib, resources, ...}:
    {
      deployment.targetEnv = "packet";
      deployment.packet = {
        inherit authToken projectId;
        hostname = "nixos-testing";
        facility = "ams1";
        plan = "baremetal_1";
        spotInstance = true;
        spotPriceMax = 6;
        userSSHKeys = [ resources.packetSSHKeys.amine ];
      };

      deployment.hasFastConnection = true;

      environment.systemPackages = [ pkgs.bind pkgs.lsof ];

      networking.firewall.enable = false;
    };

  resources.packetSSHKeys.amine =
    {
      inherit authToken;
      label = "My nixops testing key";
    };
}
