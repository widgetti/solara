<template>
    <component :is="tag" v-bind="attributes" v-html="unsafe_innerHTML">
    </component>
</template>
