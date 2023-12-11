# Troubleshoot

## Issues in Jupyter

The most common issue in the Jupyter notebook, or Jupyter Lab happens when the notebook server and the kernel do not share the same Python environment. When you install solara via the notebook (e.g. `!pip install solara`), it will install the ipyvue and ipyvuetify libraries, two of its dependencies. These libraries will get installed in the Python environment of your Python kernel.

If your Jupyter notebook or Jupyter Lab server runs in a different Python environment, your browser will not load the Javascript libraries it needs to. In order to get the server to provide these libraries to your browser, we also need to install ipyvue and ipyvuetify in the Python environment of your server.

For instance, running the following in AWS SageMaker, will give you information about the Python environment of the kernel.

```python
>>> import sys
>>> sys.executable
'/home/ec2-user/anaconda3/envs/python3/bin/python'
```

While if we inspect the output of `!ps aux | grep jupyter`, we see that the notebook server is using the Python executable at `/home/ec2-user/anaconda3/envs/JupyterSystemEnv/bin/python3.7`.

The solution is to run `!/home/ec2-user/anaconda3/envs/JupyterSystemEnv/bin/python3.7 -m pip install ipyvue ipyvuetify`, and refresh your browser.

The function `solara.check_jupyter()` will perform these checks for you and tell you what to do. However, if it fails and you
end up in this documentation, we should try to improve it by opening an [Issue on GitHub](https://github.com/widgetti/solara/issues/new).
