<template><span></span></template>
​
<script>
modules.export = {
  created() {
    history.scrollRestoration = "manual";
    if (!window.solara) {
      window.solara = {};
    }
    if (!window.solara.router) {
      window.solara.router = {};
    }
    window.solara.router.push = (href) => {
      console.log("external router push", href);
      this.location = href;
    };
    let location = window.location.href.slice(document.baseURI.length);
    // take of the anchor
    if (location.indexOf("#") !== -1) {
      location = location.slice(0, location.indexOf("#"));
    }
    this.location = "/" + location;
    window.addEventListener("popstate", this.onPopState);
    window.addEventListener("scroll", this.onScroll);
  },
  destroyed() {
    window.removeEventListener("popstate", this.onPopState);
    window.removeEventListener("scroll", this.onScroll);
  },
  methods: {
    onScroll() {
      window.history.replaceState(
        { top: document.documentElement.scrollTop },
        null,
        "." + this.location
      );
    },
    onPopState(event) {
      console.log("pop state!", event.state, window.location.pathname);
      if (!window.location.href.startsWith(document.baseURI)) {
        throw `window.location = ${window.location}, but it should start with the document.baseURI = ${document.baseURI}`;
      }
      let newLocation = "/" + window.location.href.slice(document.baseURI.length);
      // the router/server shouldn't care about the hash, that's for the frontend
      if (newLocation.indexOf("#") !== -1) {
        newLocation = newLocation.slice(0, newLocation.indexOf("#"));
      }
      this.location = newLocation;
      if (event.state) {
        const top = event.state.top;
        /*
        // we'd like to restore the scroll position, but we do not know when yet
        // maybe we will have a life cycle hook for this in the future
        setTimeout(() => {
          document.documentElement.scrollTop = top;
        }, 500);
        */
      }
    },
  },
  watch: {
    location() {
      console.log("changed", this.location);
      // if we use the back navigation, this watch will trigger,
      // but we don't want to push the history
      // otherwise we cannot go forward
      if (!window.location.href.startsWith(document.baseURI)) {
        throw `window.location = ${window.location}, but it should start with the document.baseURI = ${document.baseURI}`;
      }
      const oldLocation = "/" + window.location.href.slice(document.baseURI.length);
      console.log(
        "location changed",
        oldLocation,
        this.location,
        document.documentElement.scrollTop
      );
      if (oldLocation != this.location) {
        // we prepend with "." to make it work behind a proxy. e.g.
        // <base href="https://myserver.com/someuser/project/a/">
        window.history.pushState({ top: 0 }, null, "." + this.location);
        window.scrollTo(0, 0);
      }
    },
  },
};
</script>
