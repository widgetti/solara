# Roadmap for Solara

## Short Term

### Solara 2.0

Exciting news! Solara 2.0 should release sometime in the coming months. For the 2.0 release, we want to focus on a few things:

- Improvements to the conversion of Solara components to HTML elements. The number of wrapping elements that are generated by Solara should be drastically reduced. We also want to remove non-displayed elements that are inserted for components such as `solara.Meta`.

- Solara's `Computed` properties should be free of invalid states. This improvement should follow from us more closely implementing the ideas of [Javascript Signals](https://github.com/tc39/proposal-signals) and the pull based data update model.

- Improvements to some customization APIs, such as `solara.AppBar`.

- And more

## Medium Term

### Blog

In the medium term we hope to update the solara.dev website with a blog section where we can discuss the design decisions and philosophy behind Solara.

### Documentation

We hope to implement various improvements to the documentation. This should include the streamlining of the beginners tutorials, as well as providing documentation for some of the features that are used internally in Solara already, but that are not yet present in the documentation.

### Third-Party Solara Components

Although it is already possible to make custom components for solara, there isn't an established way to distribute them. We hope to support the development efforts of the community by providing a platform for sharing custom components easily.

## Long Term

### Different Looks

Our objective is to provide users with a robust, yet flexible front-end framework they can access directly from Python. To provide flexibility we hope to make available different front-end frameworks for users to choose from - should the user want to, `solara-ui` could be replaced completely with some other Solara compatible front-end implementation. As some users may already know, Solara is built on top of `ipyvuetify`, which provides a Python interface to the Vuetify javascript framework. However, users shouldn't be locked to that choice. We hope to one day provide similar interfaces for other front-end frameworks to fully benefit from the rich javascript ecosystem. Some efforts have already been taken towards this goal - `ipyreact` provides a touch surface to React, while we have also tried our hand at implementing [Ant Design](https://ant.design) for Solara via [ipyantd](https://github.com/widgetti/ipyantd)