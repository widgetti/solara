import os

import solara

os.environ["SERVER_SOFTWARE"] = "solara/" + str(solara.__version__)
