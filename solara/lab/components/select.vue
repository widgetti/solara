<template>
  <v-autocomplete
    :items="items"
    v-model="value"
    :messages="messages"
    :multiple="multiple"
    :return-object="return_object"
    :clearable="clearable"
    :label="label"
    class="solara-cross-filter-select"
  >
    <template v-slot:item="{ item }">
      <v-list-item-content>
        <v-list-item-title v-text="item.text"></v-list-item-title>
        <v-list-item-subtitle>
          <v-progress-linear :value="(item.count / count) * 100"></v-progress-linear>
          <div style="display: flex">
            <span v-if="count > 0"> {{ ((item.count / count) * 100).toFixed(1) }}%</span>
            <v-spacer></v-spacer>
            <span v-if="filtered"> {{ item.count }} of {{ count }} after filtering </span>
            <span v-if="!filtered">{{ item.count_max }} of {{ count }} </span>
          </div>
        </v-list-item-subtitle>
      </v-list-item-content>
    </template>
  </v-autocomplete>
</template>
