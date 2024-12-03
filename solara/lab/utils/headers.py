from typing import Dict, List, Optional, cast

from solara.toestand import Reactive

headers: Reactive[Optional[Dict[str, List[str]]]] = Reactive(cast(Optional[Dict[str, List[str]]], None), key="solara.lab.headers")
