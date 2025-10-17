import os
import sys
from urllib.parse import quote

from github import Github

# Authenticate with GitHub
access_token = os.getenv("GITHUB_TOKEN")
g = Github(access_token)


repo_name = "widgetti/solara"
commit_sha = sys.argv[1]  # e.g d39677a321bca34df41ecc87ff7e539b450207f2
run_id = sys.argv[2]  # e.g 1324, usually obtained via ${{ github.run_id }} or ${{ github.event.workflow_run.id }} in GitHub Actions workflow files
type = "solara"  # streamlit/dash/vizro/solara/panel

# your default code
code = """# this is a playground snippet using solara build on GitHub Actions
# if this link is old, the build artifact might be old, which causes the installation
# to fail
import solara

# reactive variables will trigger a component rerender
# when changed.
# When you change the default (now 0), hit the embedded browser
# refresh button to reset the state
clicks = solara.reactive(0)


@solara.component
def Page():
    print("The component render function gets called")
    # change this code, and see the output refresh
    color = "green"
    if clicks.value >= 5:
        color = "red"

    def increment():
        clicks.value += 1
        print("clicks", clicks)  # noqa

    solara.Button(label=f"Clicked: {clicks}", on_click=increment, color=color)


# Solara also supports ipywidgets
# remove the Page component and assign an ipywidget to
# the page variable, e.g.
# page = mywidget
"""

artifact_name = "solara-builds"  # name given in the GitHub Actions workflow file for the artifact

# your default requirements, the wheel version number (1.52.0) is bumped up for each new release using bump2version
requirements = f"""solara
https://py.cafe/gh/artifact/{repo_name}/actions/runs/{run_id}/{artifact_name}/solara-1.52.0-py2.py3-none-any.whl
https://py.cafe/gh/artifact/{repo_name}/actions/runs/{run_id}/{artifact_name}/solara_ui-1.52.0-py2.py3-none-any.whl
"""

# GitHub Python API
repo = g.get_repo(repo_name)

base_url = f"https://py.cafe/snippet/{type}/v1"
url = f"{base_url}#code={quote(code)}&requirements={quote(requirements)}"

# Define the deployment status
state = "success"  # Options: 'error', 'failure', 'pending', 'success'
description = "Test out this PR on a PyCafe playground environment"
context = "PyCafe"

# Create the status on the commit
commit = repo.get_commit(commit_sha)
commit.create_status(state="success", target_url=url, description=description, context="PyCafe")
print(f"Deployment status added to commit {commit_sha}")
