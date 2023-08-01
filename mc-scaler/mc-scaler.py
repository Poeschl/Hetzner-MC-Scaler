import logging
import socket
from logging import basicConfig, INFO, info
from optparse import OptionParser
from time import sleep

import docker
from docker.models.containers import Container
from hcloud import Client
from hcloud.server_types.domain import ServerType

from tools.config import read_config, save_state, ScaleState
from tools.scale_helper import scale_with_helper_host, teardown_helper_host


def scale_up_host(config: dict, client: Client):
  save_state(ScaleState.SCALED)
  scale_with_helper_host(client, ServerType(name=config['helper-type']), config['city'], config['scale-host-name'],
                         ServerType(name=config['scaled-type']))


def scale_down_host(config: dict, client: Client):
  save_state(ScaleState.STANDBY)
  scale_with_helper_host(client, ServerType(name=config['helper-type']), config['city'], config['scale-host-name'],
                         ServerType(name=config['standby-type']))


def wait_for_minecraft_socket(port: int, hex_payload: str):
  with socket.create_server(('', port)) as server:
    try:
      logging.info("Listening for: {}".format(hex_payload))

      while True:
        connection, _ = server.accept()

        data: bytes = connection.recv(1024)
        connection.close()
        logging.info("Received data: {}".format(data.hex()))

        if data.hex() == hex_payload:
          logging.info("Correct payload detected")
          break

    except socket.error as msg:
      logging.error("Network Error: {}".format(msg))
      exit(1)
    else:
      server.close()


def start_container(container_name: str):
  docker_client = docker.from_env()

  container: Container = docker_client.containers.get(container_name)
  container.start()
  logging.info("Started container: {}".format(container.name))


def is_container_running(container_name: str) -> bool:
  RUNNING = "running"
  docker_client = docker.from_env()

  try:
    container = docker_client.containers.get(container_name)
  except docker.errors.NotFound as exc:
    logging.warning("No container with that name detected!")
  else:
    container_state = container.attrs["State"]
    return container_state["Status"] == RUNNING


def main(force_scale_up: bool, force_scale_down: bool):
  current_config = read_config()
  hetzner_client = Client(token=current_config["hcloud-token"])

  info("Hetzner MC Scaler")
  info("State: {}".format(current_config["state"]))

  if force_scale_down:
    scale_down_host(current_config, hetzner_client)
  elif force_scale_up:
    scale_up_host(current_config, hetzner_client)
  else:

    teardown_helper_host(hetzner_client, current_config['scale-host-name'])

    if current_config['state'] == ScaleState.STANDBY.value:
      info("Waiting for Minecraft Client to attempt connection")

      wait_for_minecraft_socket(current_config['standby-listen-port'], current_config['standby_trigger_hex_payload'])
      scale_up_host(current_config, hetzner_client)

      # Wait for helper to scale
      sleep(10 * 60)

    else:
      info("Scaled up state detected. Starting docker container")
      start_container(current_config['running-container-name'])

      sleep(10)
      info("Waiting for docker container to shutdown")

      while is_container_running(current_config['running-container-name']):
        sleep(10)
      logging.info("Minecraft container not running any more")
      scale_down_host(current_config, hetzner_client)

      # Wait for helper to scale
      sleep(10 * 60)


if __name__ == '__main__':
  basicConfig(level=INFO, format="%(asctime)s - %(message)s",
              handlers=[logging.FileHandler("mc-scaler.log", mode='a'),
                        logging.StreamHandler()])

  parser = OptionParser()
  parser.add_option("--scale-up", help="Force the scale up of the given host.", action="store_true", dest="scale_up",
                    default=False)
  parser.add_option("--scale-down", help="Force the scale down of the given host.", action="store_true",
                    dest="scale_down", default=False)

  opts, args = parser.parse_args()
  exit(main(opts.scale_up, opts.scale_down))
