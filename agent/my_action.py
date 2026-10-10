# Compatibility import: keep main.py importing my_action while business code lives in agent/actions/.
from actions.misc import *  # noqa: F401,F403
from actions.limingjie_formation import *  # noqa: F401,F403
from actions.limingjie_shop import *  # noqa: F401,F403
from actions.shop_fragment import *  # noqa: F401,F403
