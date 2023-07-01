import logging
import os
from enum import Enum

from yaml import safe_load, YAMLError, dump


class ScaleState(Enum):
  STANDBY = 0
  SCALED = 1


CONFIG_FILE = "config.yaml"
DEFAULT_CONFIG = {"state": 0,
                  "hcloud-token": "",
                  "scale-host-name": "mc-host",
                  "standby-type": "cax11",
                  "scaled-type": "cax31",
                  "helper-type": "cax11",
                  "city": "Falkenstein",
                  "standby-listen-port:": "25565",
                  "running-container-name": "minecraft-server"}


def read_config() -> dict:
  if os.path.exists(CONFIG_FILE):
    with (open(CONFIG_FILE, "r") as configFile):
      try:
        config = safe_load(configFile)
        return config
      except YAMLError as exc:
        logging.error("Error on file config read. {}".format(exc))
        return {}
  else:
    with (open(CONFIG_FILE, "w") as configFile):
      configFile.writelines(dump(DEFAULT_CONFIG))
      return DEFAULT_CONFIG


def save_state(state: ScaleState):
  config = read_config()
  config["state"] = state.value
  with (open(CONFIG_FILE, "w") as configFile):
    configFile.writelines(dump(config))
