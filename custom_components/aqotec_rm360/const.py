"""Constants for the aqotec RM360 integration."""

from datetime import timedelta

DOMAIN = "aqotec_rm360"

CONF_DEVICE_ID = "device_id"

DEFAULT_PORT = 502
DEFAULT_DEVICE_ID = 1
DEFAULT_NAME = "aqotec RM360"

# The controller moves slowly; the fastest thing worth seeing is a tap being
# opened at the fresh water module, which a 30 second poll still catches.
UPDATE_INTERVAL = timedelta(seconds=30)

# Entity ids are fixed rather than derived from the translated names, so they
# are the same in every language and an existing setup can be renamed onto
# them ahead of time to carry its history over.
ENTITY_ID_PREFIX = "rm360"

MANUFACTURER = "aqotec GmbH"
MODEL = "RM360"
