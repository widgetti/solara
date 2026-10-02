// Shared browser runtime for solara-html components (an ipyreact ES module).
import * as React from "react";

// Returns the React component for one HTML component file.
// ipyreact passes each trait as a prop, a set<Name> setter per trait,
// each Python event as a callable prop, and the widget children.
export function defineHtmlComponent({ template, css, mount }) {
  return function HtmlComponent(props) {
    const hostRef = React.useRef(null);
    const propsRef = React.useRef(props);
    const bindingsRef = React.useRef(null);
    propsRef.current = props;

    React.useLayoutEffect(() => {
      const root = hostRef.current.shadowRoot || hostRef.current.attachShadow({ mode: "open" });
      root.replaceChildren(templateContent(template));
      if (css) {
        const sheet = new CSSStyleSheet();
        sheet.replaceSync(css);
        root.adoptedStyleSheets = [sheet];
      }
      const bindings = wireBindings(root, propsRef);
      bindingsRef.current = bindings;
      bindings.update();
      let unmounted = false;
      let cleanup = mount?.({
        root,
        get: (name) => propsRef.current[name],
        set: (name, value) => {
          if (typeof propsRef.current[setterName(name)] !== "function") warn(`set("${name}") does not match a prop`);
          setProp(propsRef.current, name, value);
        },
        subscribe: bindings.subscribe,
        // ipyreact drops an undefined argument, and the Python callback then gets no argument at all.
        emit: (action, data = null) => {
          if (typeof propsRef.current[action] !== "function") {
            warn(`emit("${action}") does not match an event`);
            return;
          }
          propsRef.current[action](data);
        },
      });
      if (typeof cleanup?.then === "function") {
        // An async mount: use the cleanup it resolves to, at once if the component already unmounted.
        const pending = cleanup;
        cleanup = null;
        pending.then(
          (resolved) => {
            if (!unmounted) cleanup = resolved;
            else if (typeof resolved === "function") resolved();
          },
          (error) => console.error("solara-html: mount failed", error),
        );
      }
      return () => {
        unmounted = true;
        if (typeof cleanup === "function") cleanup();
        bindings.dispose();
        bindingsRef.current = null;
      };
    }, []);

    // After every render: push the new props into the DOM and to subscribers.
    React.useEffect(() => bindingsRef.current?.update());

    // Children stay in the light DOM; the browser shows them at the template's <slot>.
    return React.createElement("div", { ref: hostRef }, props.children);
  };
}

function templateContent(html) {
  const element = document.createElement("template");
  element.innerHTML = html;
  return element.content.cloneNode(true);
}

function wireBindings(root, propsRef) {
  const updaters = [];
  const disposers = [];
  const subscribers = new Map();

  const listen = (element, eventName, listener) => {
    element.addEventListener(eventName, listener);
    disposers.push(() => element.removeEventListener(eventName, listener));
  };

  for (const element of root.querySelectorAll("*")) {
    for (const { name, value } of [...element.attributes]) {
      if (name.startsWith("data-solara-")) warnIfUnknown(propsRef.current, name, value);
      if (name === "data-solara-text") {
        updaters.push((props) => (element.textContent = toText(props[value])));
      } else if (name === "data-solara-model") {
        const checkbox = element.type === "checkbox";
        listen(element, checkbox ? "change" : "input", () =>
          setProp(propsRef.current, value, checkbox ? element.checked : element.value),
        );
        updaters.push((props) => setFormValue(element, props[value]));
      } else if (name.startsWith("data-solara-attr-")) {
        const attribute = name.slice("data-solara-attr-".length);
        if (!attribute || attribute === "srcdoc" || attribute.startsWith("on")) {
          warn(`${name}: cannot bind the attribute "${attribute}"`);
          continue;
        }
        updaters.push((props) => setAttribute(element, attribute, props[value]));
      } else if (name.startsWith("data-solara-event-")) {
        listen(element, name.slice("data-solara-event-".length), () => propsRef.current[value]?.(null));
      }
    }
  }

  let previous = {};
  return {
    update() {
      const props = propsRef.current;
      for (const updater of updaters) updater(props);
      for (const [name, listeners] of subscribers) {
        if (props[name] !== previous[name]) listeners.forEach((listener) => listener(props[name]));
      }
      previous = props;
    },
    subscribe(name, listener) {
      if (!subscribers.has(name)) subscribers.set(name, new Set());
      subscribers.get(name).add(listener);
      return () => subscribers.get(name)?.delete(listener);
    },
    dispose() {
      disposers.forEach((dispose) => dispose());
      subscribers.clear();
    },
  };
}

function warn(message) {
  console.warn(`solara-html: ${message}`);
}

// A typo in a binding would otherwise do nothing, silently.
function warnIfUnknown(props, binding, name) {
  if (!(name in props)) warn(`${binding}="${name}" does not match a prop or event`);
}

function setterName(name) {
  return `set${name.charAt(0).toUpperCase()}${name.slice(1)}`;
}

function setProp(props, name, value) {
  props[setterName(name)]?.(value);
}

function setFormValue(element, value) {
  if (element.type === "checkbox") {
    element.checked = Boolean(value);
  } else if (element.value !== toText(value)) {
    // Only write on a real change, so typing keeps its caret position.
    element.value = toText(value);
  }
}

const URL_ATTRIBUTES = new Set(["href", "src", "action", "formaction", "poster", "data", "xlink:href"]);
const SAFE_PROTOCOLS = new Set(["http:", "https:", "mailto:", "tel:"]);

function setAttribute(element, attribute, value) {
  const text = value === null || value === undefined || value === false ? null : value === true ? "" : String(value);
  if (text !== null && URL_ATTRIBUTES.has(attribute) && !isSafeUrl(text)) {
    warn(`refused the URL "${text}" for the attribute "${attribute}"`);
    element.removeAttribute(attribute);
  } else if (text === null) {
    element.removeAttribute(attribute);
  } else {
    try {
      element.setAttribute(attribute, text);
    } catch (error) {
      // The HTML parser accepts some names that setAttribute does not, such as one that starts with a digit.
      warn(`cannot set the attribute "${attribute}": ${error}`);
    }
  }
}

// A relative URL resolves against the page, so it gets the page's protocol.
function isSafeUrl(value) {
  try {
    return SAFE_PROTOCOLS.has(new URL(value, document.baseURI).protocol);
  } catch {
    return false;
  }
}

function toText(value) {
  return value === null || value === undefined ? "" : String(value);
}
