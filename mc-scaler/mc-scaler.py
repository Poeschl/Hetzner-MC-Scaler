import logging
from optparse import OptionParser

from hcloud.server_types.domain import ServerType

from tools.config import read_config, save_state, ScaleState
from tools.scale_helper import scale_with_helper_host
from hcloud import Client


def scale_up_host(config: dict, client: Client):
  save_state(ScaleState.SCALED)
  scale_with_helper_host(client, ServerType(name=config['helper-type']), config['city'], config['scale_host_name'], ServerType(name=config['scaled-type']))


def scale_down_host(config: dict, client: Client):
  save_state(ScaleState.STANDBY)
  scale_with_helper_host(client, ServerType(name=config['helper-type']), config['city'], config['scale_host_name'], ServerType(name=config['standby-type']))


def main(force_scale_up: bool, force_scale_down: bool):
  current_config = read_config()
  hetzner_client = Client(token=current_config["hcloud_token"])

  logging.info("Hetzner MC Scaler")
  logging.info("State: {}".format(current_config["state"]))

  if force_scale_down:
    scale_down_host(current_config, hetzner_client)
  elif force_scale_up:
    scale_up_host(current_config, hetzner_client)
  else:
    logging.info("Executing action according to the current scaling state")
    logging.error("TBD")


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)

  parser = OptionParser()
  parser.add_option("--scale-up", help="Force the scale up of the given host.", action="store_true", dest="scale_up", default=False)
  parser.add_option("--scale-down", help="Force the scale down of the given host.", action="store_true", dest="scale_down", default=False)

  opts, args = parser.parse_args()
  exit(main(opts.scale_up, opts.scale_down))
