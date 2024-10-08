# Roadmap for Solara

This roadmap is a living document that outlines the future direction of Solara. It is informed by community feedback, shaped by our vision for the project, and influenced by real-world problems we've solved for customers. If you're interested in getting involved or becoming a design partner, [contact us here](https://solara.dev/contact).


## Solara 2.0

Exciting news! We aim to release Solara 2.0 by the end of the year. For the 2.0 release, we want to focus on a few things:

- Improvements to reactive state management, closely following the principles of [Javascript Signals](https://github.com/tc39/proposal-signals) and its hybrid push-pull model. This will include glitch-free computed values and (side) effects triggered by signals.

- Elimination of common mistakes, such as detecting state mutations and avoiding misuse of hooks (e.g., using hooks in loops).

- [See more details in the 2.0 milestone on GitHub.](https://github.com/widgetti/solara/milestone/1)


## Solara 3.0

For version 3.0 we plan to switch to using ipyvue and ipyvuetify 3.0, which will be based on vue version 3.x and ipyvuetify 3.x. For the time being ipyvue and ipyvuetify 3.0 are released as alpha versions, so users of Solara do not pick these versions up. Although Solara 1.x is compatible with ipyvue 3.0, not all components are compatible with ipyvuetify 3.0. The release date for Solara 3.0 is not yet set.


## Medium Term

### Blog

In the medium term, we plan to add a blog section to the solara.dev website, where we'll discuss design decisions and the philosophy behind Solara.

### Documentation

We plan to improve the documentation by streamlining beginner tutorials and adding coverage for internal features that are currently undocumented.

### Third-Party Solara Components

While it is already possible to make custom components for Solara, there isn't an established way to distribute them. We hope to support the development efforts of the community by providing a platform for sharing custom components easily.


## Long Term

### Different Looks

Our objective is to provide users with a robust, yet flexible front-end framework they can access directly from Python. To provide flexibility we hope to make available different front-end frameworks for users to choose from - should the user want to, `solara-ui` could be replaced completely with some other Solara compatible front-end implementation. As some users may already know, Solara is built on top of `ipyvuetify`, which provides a Python interface to the Vuetify javascript framework. However, users shouldn't be locked to that choice. We hope to one day provide similar interfaces for other front-end frameworks to fully benefit from the rich javascript ecosystem. Some efforts have already been taken towards this goal - `ipyreact` provides an easy way to integrate with React from Python, making it possible to making bindings to [Ant Design](https://ant.design) for Solara via [ipyantd](https://github.com/widgetti/ipyantd)
