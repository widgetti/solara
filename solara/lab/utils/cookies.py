from typing import Dict, Optional, cast

from solara.toestand import Reactive

cookies: Reactive[Optional[Dict[str, str]]] = Reactive(cast(Optional[Dict[str, str]], None), key="solara.lab.cookies")
