#!/home/paul/miniconda3/envs/algos/bin/python3 -u

"""this script puts a bot together and launches it.
it should exist on its own as a utility used by the watchdog
DO NOT DELETE AND DO NOT TOUCH UNLESS NECESSARY
"""

import sys
from bot_utils import make_and_start_systemd_bot_service

port_name = sys.argv[1]
make_and_start_systemd_bot_service(port_name)