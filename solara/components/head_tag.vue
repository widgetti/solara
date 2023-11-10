<template><span></span></template>

<script>
module.exports = {
  mounted() {
    if (window._solaraHeadTags === undefined) {
      window._solaraHeadTags = {};
    }
    if (window._solaraHeadTags[this.key] === undefined) {
      window._solaraHeadTags[this.key] = [];
    }
    window._solaraHeadTags[this.key].push(this);
    this.updateElement();
  },
  destroyed() {
    const tags = window._solaraHeadTags[this.key];
    tags.splice(tags.indexOf(this), 1);
    // ask another headtag to update the element
    if (tags.length) {
      tags[0].updateElement();
    }
  },
  watch: {
    tagname() {
      this.updateElement();
    },
    attributes() {
      this.updateElement();
    },
    level() {
      this.updateElement();
    },
  },
  methods: {
    updateElement() {
      const tags = window._solaraHeadTags[this.key];
      let deepestTag = tags[0];
      for (let i = 1; i < tags.length; i++) {
        if (tags[i].level > deepestTag.level) {
          deepestTag = tags[i];
        }
      }
      let el = document.head.querySelector(`[data-solara-head-key="${deepestTag.tagname}-${deepestTag.key}"]`);
      if (el === null) {
        el = document.createElement(deepestTag.tagname);
        document.head.appendChild(el);
      } else {
        el.innerHTML = '';
        while (el.attributes.length > 0) {
          el.removeAttribute(el.attributes[0].name);
        }
      }
      Object.keys(deepestTag.attributes).forEach((key) => {
        el.setAttribute(key, deepestTag.attributes[key]);
      });
      el.setAttribute('data-solara-head-key', `${deepestTag.tagname}-${deepestTag.key}`);
    }
  },
};
</script>
