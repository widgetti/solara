from typing import Dict, List, Optional, cast

from solara.reactive import reactive
from solara.toestand import Reactive

headers: Reactive[Optional[Dict[str, List[str]]]] = reactive(cast(Optional[Dict[str, List[str]]], None))
