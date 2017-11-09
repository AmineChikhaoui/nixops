lib:
with lib;
{
  authToken = mkOption {
    type = types.str;
    description = ''
      The Packet.net authentication token.
    '';
  };
}
