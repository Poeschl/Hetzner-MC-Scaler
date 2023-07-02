# Hetzner MC Scaler

Some tools which allows a very comfortable on-demand Minecraft server hosting at Hetzner infrastructure.

This idea is to let a cost-effective, minimal instance run during stand-by and scale up to a instance type of your
choice wenn needed.
When a player tries to reach the not running Minecraft server at this machine, a script will be triggered and scales
itself up.
After scaling up, the minecraft server is automatically started via docker.
After the last player exits the server it will scale itself automatically down again.

## How?

In the standby state the Minecraft port will be watched for connection attempts from Minecraft clients.
If a request is received an additional cloud-host (helper) is spawned to scale up the Minecraft host machine.
For that the Minecraft host needs to be shutdown, scaled and started again from this helper.
The helper gets destroyed afterward.

In the scaled-up state the running Minecraft docker container is checked for the running state.
If it exits, because the last player leaves the server, the scale down will be executed via the helper host.

## Set up the scaling

Notice: This setup works only when you are hosting your minecraft server inside a docker container!
Its expected that this container shuts itself automatically down, when no player is online.

The setup is directly executed on the host which will be the minecraft server.
So the creation of a hetzner cloud host is not described here (but a cloud-init is given).
For setup choose the standby server type (recommendation: CAX11).

### Cloud-init script

For easy deployment of the scaled host the following cloud-init script can be used. (Ubuntu based)

```yaml
#cloud-config

package_update: true
package_upgrade: true

packages:
  - apt-transport-https
  - ca-certificates
  - curl
  - gnupg
  - lsb-release
  - python3
  - python3-pip
  - git

runcmd:
  - mkdir -p /etc/apt/keyrings
  - curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  - echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
  - apt-get update 
  - apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  - systemctl start docker
  - systemctl enable docker
  - git clone https://github.com/Poeschl/Hetzner-MC-Scaler /root/Hetzner-MC-Scaler
  - cd /root/Hetzner-MC-Scaler && pip install -r requirements.txt
  - cp /root/Hetzner-MC-Scaler/deployment/hetzner-scaler.service /etc/systemd/system
  - systemctl daemon-reload
  - systemctl start hetzner-scaler && sleep 2 && systemctl stop hetzner-scaler
  - mkdir /root/minecraft
  - reboot

```

Now your system should be setup correctly and a `config.yaml` should be showing up in the project folder at
`/root/Hetzner-MC-Scaler`. Continue in the Minecraft server setup section.

### Manual way

Install the following requirements on the host:

* Docker ([Installation](https://docs.docker.com/engine/install/ubuntu/))
* Python3 / Pip3
* systemd

After cloning this repository go inside the folder and install the required python3 packages with:

```bash
pip install -r requirements.txt
```

After that the provided systemd service file needs to be registered to allow the scaler to run in background.

```bash
cp deployment/hetzner-scaler.service /etc/systemd/system
systemctl daemon-reload
systemctl start hetzner-scaler && sleep 2 && systemctl stop hetzner-scaler 
```

After that a `config.yaml` file should appear in the project folder of the checkout out project.

You should be good to go and look at the next point about the Minecraft server.

## Set up your Minecraft server to work with the scaling

Minecraft will be running inside a docker container.
Thanks to @itzg there is a [universal minecraft image](https://github.com/itzg/docker-minecraft-server) for that.

Now create yourself a `docker-compose.yaml` file at a location of your liking.
Its content could look like this:

```yaml
version: "3"

services:
  mc:
    image: itzg/minecraft-server
    tty: true
    stdin_open: true
    ports:
      - "25565:25565"
    environment:
      EULA: "TRUE"
      RCON_CMDS_ON_DISCONNECT: save-all
      RCON_CMDS_LAST_DISCONNECT: stop
    volumes:
      # attach the relative directory 'data' to the container's /data path
      - ./data:/data
```

Make sure to have the `stop` command included in you `RCON_CMDS_LAST_DISCONNECT` settings, so that the docker container
stops automatically when the last user disconnects.

After starting the docker-compose with `docker compose up -d` for the first time you should check if you can connect
successfully and the minecraft server is set up as required.
You might need to scale up your host manually to fully test it. (Remember to leave the `Only CPU and RAM` checkbox
ticked)

Now go back to the Scaler project folder and fill out the `config.yaml`.
Adjust the standby-type and scale-type to your liking and budget.

Finally, stop the minecraft server with `docker compose stop` at the server folder.
Leave the `state` setting as it is a scale your host back to the standby server type.

After that the scaler can be started with the following commands.

```bash
systemctl enable hetzner-scaler
systemctl start hetzner-scaler
```

Now the host should scale up as soon a minecraft client tries to connect and scales down as soon the last player leaves
the server.
