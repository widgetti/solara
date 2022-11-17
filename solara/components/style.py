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
    hash = hashlib.sha256(value.encode("utf-8")).hexdigest()
    id = hash
    # ipyvue does not remove the css itself
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
        % id
    )

    template = f"""
<template>
    <span style="display: none">
    </span>
</template>
{script}
<style id="{id}">
{value}
</style>
    """
    # using .key avoids re-using the template, which causes a flicker (due to ipyvue)
    return v.VuetifyTemplate.element(template=template).key(id)
