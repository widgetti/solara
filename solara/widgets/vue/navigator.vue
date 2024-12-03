<template>
  <span></span>
</template>
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
      const url = new URL(href, window.location.origin + solara.rootPath);
      this.location = url.pathname + url.search;
      this.hash = url.hash;
    };
    let location = window.location.pathname.slice(solara.rootPath.length);
    this.location = location + window.location.search;
    this.hash = window.location.hash;
    window.addEventListener("popstate", this.onPopState);
    window.addEventListener("scroll", this.onScroll);
    window.addEventListener("hashchange", this.onHashChange);
    window.addEventListener("solara.pageReady", this.onPageLoad);
  },
  destroyed() {
    window.removeEventListener("popstate", this.onPopState);
    window.removeEventListener("scroll", this.onScroll);
    window.removeEventListener("hashchange", this.onHashChange);
    window.removeEventListener("solara.pageReady", this.onPageLoad);
  },
  methods: {
    onScroll() {
      window.history.replaceState(
        { top: document.documentElement.scrollTop },
        null,
        window.location.href
      );
    },
    onPopState(event) {
      if (!window.location.pathname.startsWith(solara.rootPath)) {
        throw `window.location.pathname = ${window.location.pathname}, but it should start with the solara.rootPath = ${solara.rootPath}`;
      }
      let newLocation = window.location.pathname.slice(solara.rootPath.length);
      this.location = newLocation + window.location.search;
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
    onHashChange(event) {
      if (!window.location.pathname.startsWith(solara.rootPath)) {
        throw `window.location.pathname = ${window.location.pathname}, but it should start with the solara.rootPath = ${solara.rootPath}`;
      }
      this.hash = window.location.hash;
    },
    onPageLoad(event) {
      if (!window.location.pathname.startsWith(solara.rootPath)) {
        throw `window.location.pathname = ${window.location.pathname}, but it should start with the solara.rootPath = ${solara.rootPath}`;
      }
      // If we've navigated to a hash with the same name on a different page the watch on hash won't trigger
      if (this.hash && this.hash === window.location.hash) {
        this.navigateToHash(this.hash);
      }
      this.hash = window.location.hash;
    },
    makeFullRelativeUrl() {
      const url = new URL(this.location, window.location.origin + solara.rootPath);
      return url.pathname + this.hash + url.search;
    },
    navigateToHash(hash) {
      const targetEl = document.getElementById(hash.slice(1));
      if (targetEl) {
        targetEl.scrollIntoView();
      }
    },
  },
  watch: {
    location(value) {
      console.log("changed", this.location, value);
      const newUrl = new URL(value, window.location);
      if(newUrl.origin != window.location.origin) {
        // external navigation
        window.location = newUrl;
        return
      }
      const pathnameNew = newUrl.pathname
      const pathnameOld = window.location.pathname
      // if we use the back navigation, this watch will trigger,
      // but we don't want to push the history
      // otherwise we cannot go forward
      if (!window.location.pathname.startsWith(solara.rootPath)) {
        throw `window.location.pathname = ${window.location.pathname}, but it should start with the solara.rootPath = ${solara.rootPath}`;
      }
      const oldLocation = window.location.pathname.slice(solara.rootPath.length) + window.location.search;
      console.log(
        "location changed",
        oldLocation,
        this.location,
        document.documentElement.scrollTop
      );
      if (oldLocation != this.location) {
        window.history.pushState({ top: 0 }, null, this.makeFullRelativeUrl());
        if (pathnameNew != pathnameOld) {
          // we scroll to the top only when we change page, not when we change
          // the search string
          window.scrollTo(0, 0);
        }
        const event = new Event('solara.router');
        window.dispatchEvent(event);
      }
    },
    hash(value) {
      if (value) {
        this.navigateToHash(value);
      }
    },
  },
  data() {
    return {
      hash: "",
    };
  },
};
</script>
