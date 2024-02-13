from typing import Dict, Optional, cast

from solara.reactive import reactive
from solara.toestand import Reactive

cookies: Reactive[Optional[Dict[str, str]]] = reactive(cast(Optional[Dict[str, str]], None))
