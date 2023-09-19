<template>
    <div style="width: fit-content;">
        <template v-if="context && use_absolute">
            <div v-for="(element, index) in activator_element"
                :key="index"
                v-on:contextmenu.prevent="show">
                <jupyter-widget :widget="element"></jupyter-widget>
            </div>
        </template>
        <template v-else-if="use_absolute">
            <div v-for="(element, index) in activator_element"
                :key="index"
                v-on:click="show">
                <jupyter-widget :widget="element"></jupyter-widget>
            </div>
        </template>
        <v-menu
            v-model="show_menu"
            :absolute="use_absolute"
            offset-y
            :position-x="x"
            :position-y="y"
        >
            <template v-if="!use_absolute" v-slot:activator="{ on }">
                <div v-on="on"
                    v-for="(element, index) in activator_element"
                    :key="index">
                    <jupyter-widget :widget="element"></jupyter-widget>
                </div>
            </template>
            <v-list v-for="(element, index) in children" :key="index" style="padding: 0;">
                <jupyter-widget :widget="element"  :style="style_" ></jupyter-widget>
            </v-list>
        </v-menu>
    </div>
</template>

<script>
module.exports = {
    data: () => ({
        x: 0,
        y: 0
    }),

    methods: {
        show(e) {
            this.show_menu = false;
            this.x = e.clientX;
            this.y = e.clientY;
            this.$nextTick(() => {
                this.show_menu = true;
            });
        }
    }
}
</script>
