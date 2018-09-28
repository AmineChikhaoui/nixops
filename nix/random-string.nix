{ config, lib, ... }:

with lib;

{

  options = {

    length = mkOption {
      type = types.int;
      description = ''
        length of the randomly generated string.
      '';
    };

    generatedString = mkOption {
      default = "_UNKNOWN_";
      type = types.str;
      description = "The randomly generated string by NixOps";
    };

  };

  config._type = "random-string";

}
