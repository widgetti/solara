# Making a Vue based component

If based on [./make-components](./make-components) you made the decision to write a vue based component, this article will guide you through the process.

This howto is an extended version of [https://solara.dev/documentation/examples/general/vue_component]

[https://solara.dev/documentation/api/utilities/component_vue]

We will first start with a component which is meant to be use inside of a single application, which will fetch the 3rd party library from a CDN. The goal
is to get something work with the minimal amount of effort.

Our goal is to create a button, that when clicked, will show confetti.

## The skeleton setup.

First, we create our minimal `button-confetti.vue` file which includes a very simple button with a custom label and a click event handler.
```vue
<template>
    <button class="button-confetti" @click="click({extra: 'foo'}) ">
        \{\{ label \}\}
    </button>
</template>
```


To expose this vue component to Solara, we use [the component_vue decorator](/documentation/api/utilities/component_vue).


```python
import solara
from typing import Callable

@solara.component_vue("button-confetti.vue")
def ButtonConfetti(
    label: str = "Default label",
    event_click: Callable = None,
    ):
    ...

@solara.component
def Page():
   ButtonConfetti(label="Click me", event_click=print)
```

This simple app will show a button with the label "Click me" and when clicked, it will print `{'extra': 'foo'}` to the console. [<img src="https://py.cafe/logos/pycafe_logo.png" alt="PyCafe logo" width="24" height="24"> Run and edit this example at PyCafe](https://py.cafe/maartenbreddels/solara-howto-component-vue-A).


## Loading the confetti library.

Now that we have our skeleton setup, we can add the confetti library. We will use the [`canvas-confetti`](https://www.npmjs.com/package/canvas-confetti) library, which is available on a CDN. We will add this to our `button-confetti.vue` file with unfortunately a bit of boilerplate code to load the library.:

```vue
<template>
    <button class="button-confetti" @click="clickHandler">
        {{label}}
    </button>
</template>
<script>
module.exports = {
    created() {
        console.log("button-confetti: created");
        this.loadedConfetti = this.loadConfetti();
    },
    mounted() {
        console.log("button-confetti: mounted");
    },
    watch: {
        label() {
            console.log("button-confetti: label changed");
        }
    },
    methods: {
        clickHandler() {
            if(this.click) {
                this.click({extra: 'foo'})
            }
            this.showConfetti();
        },
        async showConfetti() {
            // make sure it is loaded by waiting on the Promise
            await this.loadedConfetti;
            await new Promise((resolve) => setTimeout(resolve, 1000))
            confetti();
        },
        /* begin boilerplate */
        async loadConfetti() {
            let confettiUrl = "https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.3/dist/confetti.browser.min.js";
            require.config({
                map: {
                    '*': {
                        'confetti': confettiUrl,
                    }
                }
            })
            await new Promise((resolve, reject) => {
                require(['confetti'], (confettiModule) => {
                    resolve(confettiModule);
                }, reject)
            });
        },
        /* end boilerplate */
    },
}
</script>
<style id="button-confetti">
    .button-confetti {
        background-color: lightblue;
        margin: 10px;
        padding: 4px;
        border: 1px solid black;
    }
</style>
```

[<img src="https://py.cafe/logos/pycafe_logo.png" alt="PyCafe logo" width="24" height="24"> Run and edit this example at PyCafe](https://py.cafe/maartenbreddels/solara-howto-component-vue-B).


## Triggering the confetti from the Python side

Although we have a working button showing out confetti, this is triggered by a button in our vue template. There are situations where we want to trigger the confetti from the Python side. We can do this by making our
Vue component respond to its argument in the `watch` section. We also remove any vue from out template so that our vue template becomes a non-visual component.

Our Python code simply passes an integer (named `trigger`) to the Vue component. When this integer changes, the confetti should be shown.
```python
import solara
from typing import Callable

@solara.component_vue("confetti.vue")
def Confetti(trigger: int):
    ...

@solara.component
def Page():
    trigger = solara.use_reactive(0)
    def on_click():
        trigger.value += 1
    with solara.Row():
        solara.Button("Confetti", on_click=on_click, color="primary")
        Confetti(trigger=trigger.value)
```

Our vue component
```vue
<template>
</template>
<script>
module.exports = {
    created() {
        console.log("confetti: created");
        this.loadedConfetti = this.loadConfetti();
    },
    mounted() {
        console.log("confetti: mounted");
    },
    watch: {
        trigger(value) {
            console.log("confetti: trigger value changed to", value);
            this.showConfetti();
        }
    },
    methods: {
        clickHandler() {
            if(this.click) {
                this.click({extra: 'foo'})
            }
            this.showConfetti();
        },
        async showConfetti() {
            // make sure it is loaded by waiting on the Promise
            await this.loadedConfetti;
            confetti();
        },
        /* begin boilerplate */
        async loadConfetti() {
            let confettiUrl = "https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.3/dist/confetti.browser.min.js";
            require.config({
                map: {
                    '*': {
                        'confetti': confettiUrl,
                    }
                }
            })
            await new Promise((resolve, reject) => {
                require(['confetti'], (confettiModule) => {
                    resolve(confettiModule);
                }, reject)
            });
        },
        /* end boilerplate */
    },
}
</script>

```

[<img src="https://py.cafe/logos/pycafe_logo.png" alt="PyCafe logo" width="24" height="24"> Run and edit this example at PyCafe](https://py.cafe/maartenbreddels/solara-howto-component-vue-C).
