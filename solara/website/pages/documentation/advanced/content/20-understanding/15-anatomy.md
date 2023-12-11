# Anatomy

For communication, it is useful to speak the same language and use the same idiom.
As a reference, we provide this "anatomy" image of our favorite `ClickButton` component with a layout that we consider best practice.

![anatomy](https://dxhl76zpt6fap.cloudfront.net/public/docs/anatomy.webp)

## Explanations

 * Import `solara` and you also get the `reacton` namespace with it (saves typing, and finding/remembering which hooks is in which packages)
 * Add a `@solara.component` decorator to turn your function into a component.
 * Start with `use_state` hooks and other hooks. This avoids issues with [conditional hooks](/docs/understanding/rules-of-hooks) or hooks in loops.
 * Data/state flows down (to children)
 * Information (events, data) flows up from children via events and callbacks (`on_<some_event_name>=my_callback`).
 * If you need multiple components, use a [parent container component](/api#layout) as context manager. A good default name to give this context manager is `main`. Don't forget to return it in your render function!
 * The body of your component (the function you wrote) is called the render function.
 * In between the hooks as defining all your elements, you put your custom code, like checking variables, defining callbacks, and other logic.
 * The only way for a component to cause itself to rerender is to have state (using `use_state`) and change it (calling the second return value with a different value).
 * Reacton is declarative. Your render function gets executed after every state change (and thus should be relatively cheap to execute). Reacton will find out the changes for you and will add, remove and update the associated widgets for you. This means you can easily do conditional rendering (creating an element in an if statement or in a loop).
