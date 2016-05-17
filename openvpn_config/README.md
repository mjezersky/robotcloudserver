#Robot Management Cloud Server

## OpenVPN configuration
In this folder, you can find two files that can be used for server configuration - one of them handles robots on port 2105, and the other handles robots, on port 2106.

To get this setup to work, you first need to generate keys, which is what an open-source tool **easy-rsa** [(link)](https://openvpn.net/index.php/open-source/documentation/miscellaneous/77-rsa-key-management.html) can be used.

## RSA keys and certificates
To make this process easier, a bash script has been made, utilizing OpenVPN's easy-rsa.
Fist of all, however, you need to set up both user-side easy-rsa and the robot-side one. You do this by navigating into the folders **rsa_generator/easy-rsa/robotside** and **rsa_generator/easy-rsa/userside**, and setting up and copying server keys and certificates,
renaming them accorting to the configuration files.
Manual for easy-rsa is available  [here](https://openvpn.net/index.php/open-source/documentation/miscellaneous/77-rsa-key-management.html).

Once the basic setup is done, you are ready to generate keys for user and robot clients, which is described in the following section.

## Generating client keys

First of all, you need to edit the following files: **rsa_generator/easy-rsa/userclient.conf** and **rsa_generator/easy-rsa/robotclient.conf**.
In these files, you need to find a line with "remote" settings, which describes the IP address and the port of the VPN server, there you put the public IP of your server.

For example, if you have a server at 123.456.789.012, and you use the supplied server configuration, you change the line to the following:
**remote 123.456.789.012 2105** for rsa_generator/easy-rsa/robotclient.conf
and
**remote 123.456.789.012 2106** for rsa_generator/easy-rsa/userclient.conf

Once you have edited these two files, you are ready to generate client-side configurations.
When you launch **generate_config.sh**, you will be given an option, where you choose whether to generate configuration for a robot or for a user.
Then you select a name for the configuration package. Once this is done, easy-rsa will launch and you need to confirm all the prompts. If you have
set up your easy-rsa correctly, all you need to do is leave everything blank and confirm it with enter key, with the exception of the last two lines,
which need to be confirmed by "y" and enter.

Once the script is finished, you can find tarballs in the folders of **rsa_generator/keys/userside** and **rsa_generator/keys/robotside**.
If everything was set up according to this manual and to the one on easy-rsa, this tar archive should be a fully functional Open-VPN client configuration. All you need to do
is to extract the archive into **/etc/openvpn/** and restart OpenVPN with **service openvpn restart** (might need sudo priveleges). VPN should report launching successfully,
and if your server is running and reachable, it should connect in few seconds. This can be verified with **ifconfig**, and in case something went wrong, the errors can be seen in **syslog**.