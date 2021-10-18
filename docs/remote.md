# Remote
To make it easier for your guests to access Raveberry on your Raspberry Pi, you can use the remote feature. It allows you to connect it with a server you own, so people can visit your Raveberry instance through your public server. This is useful if you want to keep the mobility and local playback capability of your Raspberry Pi and combine it with the ease of access of a public webpage.

In order to make use of this feature, you need a server that:
* is reachable via a global url or IP
* allows Raveberry to connect via the given ssh key
* forwards traffic to Raveberry

Here are some minimal example steps that should get you started.
First, generate an ssh keypair on your Raspberry Pi and copy it to your server:
```
ssh-keygen -t rsa -b 4096 -f raveberry_remote
scp raveberry_remote.pub you@<server_ip>:
```
The absolute path of the private key needs to be specified in the config file as `remote_key`.

On your server, create a `raveberry` user and associate it with your keypair.
Using a seperate user without a shell minimizes damage potential in case your key gets compromised.
Run these commands as root.
```
useradd -m -s /sbin/nologin raveberry
mkdir /home/raveberry/.ssh
chmod 700 /home/raveberry/.ssh
cp raveberry_remote.pub /home/raveberry/.ssh/authorized_keys
chmod 600 /home/raveberry/.ssh/authorized_keys
chown raveberry:raveberry -R /home/raveberry/.ssh
```

Lastly, you need to configure a webserver to forward traffic to the port Raveberry is connected to. An example nginx config can be found in [raveberry-remote](raveberry-remote). With this config, your `remote_port` would be 8266.
