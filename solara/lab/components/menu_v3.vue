<template>
    <v-menu
        v-model="show_menu"
        :target="context ? menu_target : undefined"
        :location="context ? undefined : 'bottom'"
        :offset="4"
        :close-on-content-click="close_on_content_click"
        :min-width="use_activator_width ? null : 'auto'"
    >
        <template v-if="context" v-slot:activator>
            <div v-for="(element, index) in activator"
                :key="index"
                @contextmenu.prevent="show($event)">
                <jupyter-widget :widget="element"></jupyter-widget>
            </div>
        </template>
        <template v-else v-slot:activator="{ props }">
            <div v-for="(element, index) in activator" :key="index" v-bind="props">
                <jupyter-widget :widget="element"></jupyter-widget>
            </div>
        </template>
        <v-list v-for="(element, index) in children" :key="index" style="padding: 0;">
            <jupyter-widget :widget="element" :style="style"></jupyter-widget>
        </v-list>
    </v-menu>
</template>

<script>
module.exports = {
    data() {
        return {
            menu_target: undefined,
        }
    },
    methods: {
        show(e) {
            this.show_menu = false;
            this.menu_target = [e.clientX, e.clientY];
            this.$nextTick(() => {
                this.show_menu = true;
            })
        }
    }
}
</script>
