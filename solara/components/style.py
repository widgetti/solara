import hashlib

import ipyvuetify as v

import solara


@solara.component
def Style(value: str = ""):
    """Add a custom piece of CSS.

    Note that this is considered an advanced feature, and should be used with caution.

    ## Arguments

    - `value`: The CSS string to insert into the page.
    """
    uuid = solara.use_unique_key()
    hash = hashlib.sha256(value.encode("utf-8")).hexdigest()
    # the key is unique for this component + value
    # so that we create a new component if the value changes
    # but we do not remove the css of a component with the same value
    key = uuid + "-" + hash
    # ipyvue does not remove the css itself, so we need to do it manually
    script = (
        """
<script>
module.exports = {
  destroyed() {
    document.getElementById("ipyvue-%s").remove();
  },
};
</script>
    """
        % key
    )

    template = f"""
<template>
    <span style="display: none">
    </span>
</template>
{script}
<style id="{key}">
{value}
</style>
    """
    # using .key avoids re-using the template, which causes a flicker (due to ipyvue)
    return v.VuetifyTemplate.element(template=template).key(key)
