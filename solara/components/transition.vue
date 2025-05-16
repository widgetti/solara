<template>
    <Transition :name="name" :mode="mode" :duration="duration">
        <jupyter-widget v-if="show_first && children.length > 0" :widget="children[0]" key="first-widget"></jupyter-widget>
        <jupyter-widget v-if="!show_first && children.length > 1" :widget="children[1]" key="second-widget"></jupyter-widget>
    </Transition>
</template>
