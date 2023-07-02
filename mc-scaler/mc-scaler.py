import logging
import socket
from logging import basicConfig, INFO, info
from optparse import OptionParser
from time import sleep
from typing import List

import docker
from docker.models.containers import Container
from hcloud import Client
from hcloud.server_types.domain import ServerType

from tools.config import read_config, save_state, ScaleState
from tools.scale_helper import scale_with_helper_host


def scale_up_host(config: dict, client: Client):
  save_state(ScaleState.SCALED)
  scale_with_helper_host(client, ServerType(name=config['helper-type']), config['city'], config['scale-host-name'], ServerType(name=config['scaled-type']))


def scale_down_host(config: dict, client: Client):
  save_state(ScaleState.STANDBY)
  scale_with_helper_host(client, ServerType(name=config['helper-type']), config['city'], config['scale-host-name'], ServerType(name=config['standby-type']))


def wait_for_minecraft_socket(port: int):
  MC_PAYLOAD = '\x16\x00ò\x05\x0f'

  try:
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_socket.bind(('', port))
    listen_socket.listen(1)

    listening = True
    while listening:
      connection, _ = listen_socket.accept()

      data: bytes = connection.recv(1024)
      buffer = data.decode("ansi")

      logging.info("Received data: {}".format(buffer))
      if MC_PAYLOAD in buffer:
        listening = False

  except socket.error as msg:
    logging.error("Network Error: {}".format(msg))
    exit(1)


def start_container(container_name: str):
  docker_client = docker.from_env()

  container: List[Container] = docker_client.containers.list(filters={"id": container_name})
  logging.debug(container)
  container[0].start()


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
    if current_config['state'] == ScaleState.STANDBY.value:
      info("Waiting for Minecraft Client to attempt connection")

      wait_for_minecraft_socket(current_config['standby-listen-port'])
      logging.info("Minecraft payload detected")
      scale_up_host(current_config, hetzner_client)

    else:
      info("Scaled up state detected. Starting docker container")
      start_container(current_config['running-container-name'])

      info("Waiting for docker container to shutdown")

      while is_container_running(current_config['running-container-name']):
        sleep(60)
      logging.info("Minecraft container not running any more")
      scale_down_host(current_config, hetzner_client)


if __name__ == '__main__':
  basicConfig(level=INFO)

  parser = OptionParser()
  parser.add_option("--scale-up", help="Force the scale up of the given host.", action="store_true", dest="scale_up", default=False)
  parser.add_option("--scale-down", help="Force the scale down of the given host.", action="store_true", dest="scale_down", default=False)

  opts, args = parser.parse_args()
  exit(main(opts.scale_up, opts.scale_down))
