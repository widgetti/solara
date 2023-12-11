"""# Deploy model demo

This show off a combination of [solara.lab.Menu](/api/menu) and [solara.lab.ConfirmationDialog](/api/confirmation_dialog)
and [solara.use_thread](/api/use_thread) to demonstrate how to tune, fit and deploy a model.
The actually deployment is not real, but simulated by a thread that returns a boolean value on success and sleep for a while to
similate the deployment taking time.

 * Right click on the plot to either fit or reset the model parameters.
 * Clicking on the button shows a custom menu to deploy to several environments.
 * A confirmation dialog is used before executing the deployment.
 * If the deployment fails, a confirmation dialog is shown to retry the deployment.
"""
import time

import numpy as np
import pandas as pd
import plotly.express as px

import solara
import solara.lab

slope = solara.reactive(1.5)
intercept = solara.reactive(0.5)

x = np.arange(0, 100, 2) / 10
# fake data with noise
y_data = (slope.value * 0.8) * x + (intercept.value + 0.4) + np.random.normal(0, 0.5, len(x))


@solara.component
def Page():
    deploy_environment_request = solara.use_reactive("")
    deploy_environment = solara.use_reactive("")
    fake_failed = solara.use_reactive(False)

    def deploy_model():
        if deploy_environment.value == "":
            return

        # 'dummy' deployment
        time.sleep(1.5)

        # fake a failure the first time
        if not fake_failed.value:
            fake_failed.value = True
            return False
        else:
            return True

    deploy_state: solara.Result[bool] = solara.use_thread(deploy_model, dependencies=[deploy_environment.value])

    x_model = x
    y_model = (slope.value) * x_model + (intercept.value)
    df1 = pd.DataFrame({"x": x, "y": y_data})
    df2 = pd.DataFrame({"x": x_model, "y": y_model})
    df = pd.concat([df1, df2], keys=["data", "model"], names=["type"]).reset_index()
    fig = px.line(df, x="x", y="y", color="type")
    with solara.Card("My fancy model"):
        fig_element = solara.FigurePlotly(fig)

        def reset():
            slope.set(1.5)
            intercept.set(0.5)

        def fit():
            slope.set(1.5 * 0.8)
            intercept.set(0.9)

        with solara.lab.ContextMenu(activator=fig_element):
            solara.Button("Reset", text=True, icon_name="mdi-refresh", on_click=reset)
            solara.Button("Fit", text=True, icon_name="mdi-brain", on_click=fit)

        solara.FloatSlider("Slope", value=slope, min=-2, max=5, step=0.1)
        solara.FloatSlider("Intercept", value=intercept, min=-10, max=10, step=0.1)

        solara.lab.ConfirmationDialog(
            deploy_environment_request.value != "",
            title="Confirm deployment",
            content=solara.Markdown(f"Are you sure you want to deploy to **{deploy_environment_request.value}**?"),
            ok=f"Deploy to {deploy_environment_request.value}",
            on_ok=lambda: deploy_environment.set(deploy_environment_request.value),
            on_close=lambda: deploy_environment_request.set(""),
        )

        solara.lab.ConfirmationDialog(
            deploy_state.value is False and deploy_state.state == solara.ResultState.FINISHED,
            title="Deployment failed",
            on_close=lambda: None,
            on_ok=lambda: deploy_state.retry(),
            content=solara.Error(solara.Markdown(f"Deployment to **{deploy_environment.value}** failed. Do you want to try again?")),
            ok="Retry deployment",
            cancel="Ignore the failure",
        )

        def request_deploy(environment):
            deploy_environment.value = ""
            deploy_environment_request.set(environment)

        deploying = bool(deploy_environment.value and deploy_state.state == solara.ResultState.RUNNING)
        deploy_button = solara.Button("Deploy model", color="primary", icon_name="mdi-rocket", loading=deploying)
        with solara.lab.Menu(activator=deploy_button):
            with solara.Column(gap="0px"):
                solara.Button("Deploy to testing environment", text=True, icon_name="mdi-bug", on_click=lambda: request_deploy("testing"))
                solara.Button("Deploy to staging environment", text=True, icon_name="mdi-test-tube", on_click=lambda: request_deploy("staging"))
                solara.Button(
                    "Deploy to production",
                    text=True,
                    icon_name="mdi-rocket",
                    style={"justify-content": "left"},  # make the icon appear on the left
                    on_click=lambda: request_deploy("production"),
                )
        if deploy_state.value is True and deploy_state.state == solara.ResultState.FINISHED:
            # add some margin in the y direction using my-4
            solara.Success(solara.Markdown(f"Model deployed successfully to **{deploy_environment.value}**!"), classes=["my-4"])
