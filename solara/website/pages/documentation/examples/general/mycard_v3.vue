<template>
    <v-card class="text-center" :color="color" theme="dark">
        <v-card-text>
            <v-sheet color="rgba(0, 0, 0, .12)">
                <v-sparkline :model-value="value" color="rgba(255, 255, 255, .7)" height="100" padding="24" stroke-linecap="round"
                    smooth>
                    <template v-slot:label="item">
                        ${{ item.value }}
                    </template>
                </v-sparkline>
            </v-sheet>
        </v-card-text>

        <v-card-text>
            <h1 class="solara-some-class">{{ caption }}</h1>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions class="justify-center">
            <v-btn block variant="text" @click="goto_report">
                Go to Report
            </v-btn>
        </v-card-actions>
    </v-card>
</template>
<style id="mycard">
.solara-some-class {
    font-weight: lighter;
}
</style>

<script>
export default {
    data: () => ({
        value: [
            423,
            446,
            675,
            510,
            590,
            610,
            760,
        ],
    }),
    mounted: () => {
        console.log('mounted');
    },
    unmounted: () => {
        console.log('destroyed');
    },
    watch: {
        value: function (val) {
            console.log('value changed to', val);
        }
    }
}
</script>
