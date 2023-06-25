# Hetzner MC Scaler

Some tools which allows a very comfortable on-demand Minecraft server hosting at Hetzner infrastructure.

This idea is to let a cost-effective, minimal instance run during stand-by and scale up to a instance type of your choice wenn needed.
When a player tries to reach the not running Minecraft server at this machine, a script will be triggered and scales itself up.
After scaling up, the minecraft server is automatically started via docker.
After the last player exits the server it will scale itself automatically down again.

## Setup

### Requirements on the instance for scaling

```bash
apt-get install -y python3
pip3 install -r requirements.txt
```

//TBD (This ist still in progress)
