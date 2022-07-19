A bundle that is used for solara-server that includes all static assets we need.

For a dev install, use something like so that the Solara CDN proxy picks up the bundle locally:

    $ ln -s /Users/maartenbreddels/github/widgetti/solara/packages/solara-vuetify-app/dist/ ~/miniconda3/envs/dev/share/solara/cdn/@widgetti/solara-vuetify-app@1.0.0/dist
