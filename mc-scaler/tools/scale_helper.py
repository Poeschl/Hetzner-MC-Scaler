import logging

from hcloud import Client
from hcloud.images.domain import Image
from hcloud.server_types.domain import ServerType
from hcloud.servers.domain import ServerCreatePublicNetwork


def scale_with_helper_host(client: Client, helper_type: ServerType, city: str, scale_host_name: str, scale_type: ServerType):
  helper_host_name = "{}-helper".format(scale_host_name)

  logging.info("Start scaling via an helper (%s,%s). Target host '%s' scaling to %s", helper_host_name, helper_type.name, scale_host_name, scale_type.name)

  existing_scale_helper = client.servers.get_by_name(name=helper_host_name)
  if existing_scale_helper is not None:
    logging.info("Cleanup helper instance first")
    teardown_helper_host(client, scale_host_name)

  host_location = None
  for location in client.locations.get_all():
    if location.city == city:
      host_location = location

  scale_host = client.servers.get_by_name(scale_host_name)

  user_data = """
    #cloud-config
    
    keyboard:
      layout: de
      
    packages:
      - jq
      
    write_files:
      - path: /root/start.sh
        owner: root:root
        permissions: '0755'
        content: |
          #!/usr/bin/env bash
          set -e
          
          echo "Shutdown scaling host"
          curl -X POST -H 'Authorization: Bearer {token}' 'https://api.hetzner.cloud/v1/servers/{id}/actions/shutdown'
          
          STATUS=""
          while [[ ! "$STATUS" == "off" ]]; do
            echo "Waiting for shutdown of scaling host"
            sleep 2
            RESPONSE=$(curl -s -H 'Authorization: Bearer {token}' 'https://api.hetzner.cloud/v1/servers/{id}')
            STATUS=$(echo $RESPONSE | jq --raw-output '.server.status' )
            echo "Status: $STATUS"
          done  
          
          echo "Scaling host"
          curl -X POST -H 'Authorization: Bearer {token}' -H 'Content-Type: application/json' \
            -d '{{"server_type":"{scale_type}","upgrade_disk":false}}' 'https://api.hetzner.cloud/v1/servers/{id}/actions/change_type'
          
          echo "Shutdown"
          shutdown -h now
      
    runcmd:
      - "/root/start.sh"
  """.format(token=client.token, id=scale_host.data_model.id, scale_type=scale_type.name)

  scale_helper = client.servers.create(name=helper_host_name,
                                       server_type=helper_type,
                                       image=Image(name="ubuntu-22.04"),
                                       location=host_location,
                                       public_net=ServerCreatePublicNetwork(enable_ipv4=False, enable_ipv6=True),
                                       user_data=user_data)
  logging.info("Started %s with root passwd: %s", scale_helper.server.name, scale_helper.root_password)


def teardown_helper_host(client: Client, scale_host_name: str):
  helper = client.servers.get_by_name("{}-helper".format(scale_host_name))

  if helper is not None:
    logging.info("Cleanup helper instance")
    client.servers.delete(helper)
