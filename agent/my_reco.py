# Compatibility import: keep main.py importing my_reco while recognition code lives in agent/recognitions/.
from recognitions.common import *  # noqa: F401,F403
