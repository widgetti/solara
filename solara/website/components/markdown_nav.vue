<template>
    <v-list dense :style="`margin: 40px 24px 0 24px; position: sticky; top: 88px; align-self: flex-start;`" class="d-none d-lg-inline-block">
        <v-list-item
            v-for="(element, index) in this.sections"
            :key="index"
            :href="'#' + element.id"
            :style="'padding-left: ' + (16 + (element.nodeName[1] - 1) * 20) + 'px;'"
        >
            <v-list-item-content>
                <v-list-item-title>
                    {{ element.innerText }}
                </v-list-item-title>
            </v-list-item-content>
        </v-list-item>
    </v-list>
</template>
<script>
module.exports = {
    mounted() {
        this.getSections();
    },
    methods: {
        getSections() {
            const parentToSearch = document.getElementById(this.id);
            this.sections = parentToSearch.querySelectorAll('h1, h2, h3, h4');
        },
    },
    data() {
        return {
            sections: []
        }
    }
}
</script>
