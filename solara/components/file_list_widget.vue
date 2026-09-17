<template>
  <v-sheet class="solara-file-list" ref="scrollpane"
      @click="clicked = null"
  >
    <v-list
      @click="clicked = null"
    >
      <v-list-item
          v-for="{name, is_file, size} in files"
          :key="name + '|' + is_file"
          @click.stop="emitClick(name, is_file)"
          @dblclick="emitDoubleClick(name, is_file)"
          :ripple="!use_selected_names || !isSelected(name)"
          :class="isSelected(name) ? 'solara-file-list-selected': ''"
      >
        <v-list-item-icon>
          <v-icon>{{ name === '..' ? 'mdi-keyboard-backspace' : is_file ? 'mdi-file-document' : 'mdi-folder' }}</v-icon>
        </v-list-item-icon>

        <v-list-item-content>
          <v-list-item-title :class="'solara-file-list-' + (is_file ? 'file' : 'dir')">
            {{ name }}<span v-if="size"> - {{ size }}</span>
          </v-list-item-title>
        </v-list-item-content>
      </v-list-item>
    </v-list>
  </v-sheet>
</template>

<script>
module.exports = {
  data() {
    return {
      click_id: 0,
      // Keep multiple-selection highlighting local until Python confirms it;
      // otherwise toggling an already selected row visibly waits for the trait round trip.
      // When a row is already selected, disable Vuetify ripple because it animates
      // over the selected background and looks like selection jitter during deselect.
      optimistic_selected_names: this.selected_names || [],
    }
  },
  methods: {
    emitClick(name, is_file) {
      this.click_id += 1
      if (this.use_selected_names && name !== '..') {
        const selected = this.optimistic_selected_names || []
        if (selected.indexOf(name) === -1) {
          this.optimistic_selected_names = selected.concat([name])
        } else {
          this.optimistic_selected_names = selected.filter(item => item !== name)
        }
      }
      this.clicked = { name, is_file }
      this.click_event = { name, is_file, click_id: this.click_id }
    },
    emitDoubleClick(name, is_file) {
      this.click_id += 1
      this.double_clicked = { name, is_file }
      this.double_click_event = { name, is_file, click_id: this.click_id }
    },
    isSelected(name) {
      if (this.use_selected_names) {
        return (this.optimistic_selected_names || []).indexOf(name) !== -1
      }
      return this.clicked && this.clicked.name === name
    }
  },
  mounted() {
    const element = this.$refs.scrollpane.$el
    element.scrollTop = this.scroll_pos

    this._scrollListener = _.debounce((e) => {
      this.scroll_pos = Math.round(element.scrollTop)
    }, 50)
    element.addEventListener('scroll', this._scrollListener)
  },
  watch: {
    selected_names(v) {
      this.optimistic_selected_names = v || []
    },
    scroll_pos(v) {
      this.$nextTick(() => this.$refs.scrollpane.$el.scrollTop = v);
    }
  }
}
</script>

<style id="solara-file-list">
.solara-file-list {
  height: 400px;
  overflow: auto;
}

.solara-file-list-dir {
  font-weight: bold;
}

.solara-file-list-selected {
  background-color: #3333;

}

.solara-file-list .v-list-item__icon,
.solara-file-list .v-list-item__list {
  margin-top: 0;
  margin-bottom: 0;
}

.v-application--is-ltr .solara-file-list .v-list-item__icon {
  margin-right: 8px;
}

.solara-file-list .v-list-item {
  height: 28px;
  min-height: 0;
  padding-left: 0;
}
</style>
