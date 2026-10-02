<template>
  <v-sheet class="solara-file-list" ref="scrollpane"
      @click="clearSelection"
  >
    <v-list
      @click="clearSelection"
    >
      <v-list-item
          v-for="{name, is_file, size} in files"
          :key="name + '|' + is_file"
          @click.stop="emitClick(name, is_file, $event)"
          @mousedown.shift.prevent
          @dblclick="emitDoubleClick(name, is_file)"
          :ripple="!use_selected_names || !isSelected(name)"
          :class="['solara-file-list-item', isSelected(name) ? 'solara-file-list-selected': '']"
      >
        <div class="solara-file-list-row">
          <div class="solara-file-list-icon">
            <v-icon class="text-medium-emphasis">{{ name === '..' ? 'mdi-keyboard-backspace' : is_file ? 'mdi-file-document' : 'mdi-folder' }}</v-icon>
          </div>
          <v-list-item-title :class="'solara-file-list-' + (is_file ? 'file' : 'dir')">
            {{ name }}<span v-if="size"> - {{ size }}</span>
          </v-list-item-title>
        </div>
      </v-list-item>
    </v-list>
  </v-sheet>
</template>

<script>
module.exports = {
  data() {
    return {
      click_id: this.selection_state ? this.selection_state.click_id : 0,
      selection_anchor: null,
      range_base: null,
      // Match the Vue 2 template: update highlighting before the Python round trip.
      optimistic_selected_names: this.selected_names || [],
    }
  },
  methods: {
    resetSelectionGesture() {
      this.selection_anchor = null
      this.range_base = null
    },
    clearSelection() {
      this.resetSelectionGesture()
      if (this.use_selected_names) this.optimistic_selected_names = []
      this.clicked = null
    },
    emitClick(name, is_file, event) {
      this.click_id += 1
      let range_selection = null
      if (this.use_selected_names && name !== '..') {
        const selected = this.optimistic_selected_names || []
        const names = this.files.map(file => file.name).filter(name => name !== '..')
        const anchor = names.indexOf(this.selection_anchor)
        if (event.shiftKey && anchor !== -1) {
          if (this.range_base === null) this.range_base = selected.slice()
          const end = names.indexOf(name)
          const range = names.slice(Math.min(anchor, end), Math.max(anchor, end) + 1)
          range_selection = Array.from(new Set(this.range_base.concat(range)))
          this.optimistic_selected_names = range_selection
        } else {
          this.selection_anchor = name
          this.range_base = null
          this.optimistic_selected_names = event.shiftKey || !selected.includes(name)
            ? Array.from(new Set(selected.concat([name])))
            : selected.filter(item => item !== name)
          if (event.shiftKey) range_selection = this.optimistic_selected_names
        }
      }
      this.clicked = { name, is_file }
      this.click_event = { name, is_file, click_id: this.click_id, location: this.location, selected_names: range_selection }
    },
    emitDoubleClick(name, is_file) {
      this.resetSelectionGesture()
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
      if (!this.selection_state) this.optimistic_selected_names = v || []
    },
    selection_state(v) {
      // Match the reply to its click, even when consecutive ranges select the same names.
      if (!v || v.click_id < this.click_id) return
      if (!_.isEqual(v.names, this.optimistic_selected_names)) this.resetSelectionGesture()
      this.optimistic_selected_names = v.names
    },
    files() {
      this.resetSelectionGesture()
    },
    location() {
      this.resetSelectionGesture()
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

.solara-file-list .solara-file-list-row {
  align-items: center;
  display: flex;
  min-height: 28px;
  width: 100%;
}

.solara-file-list .solara-file-list-icon {
  align-items: center;
  display: flex;
  flex: 0 0 32px;
  justify-content: center;
  margin-right: 8px;
}

.solara-file-list .solara-file-list-item.v-list-item,
.solara-file-list .v-list-item {
  height: 28px;
  min-height: 0;
  padding: 0;
  padding-inline-end: 0;
  padding-inline-start: 0;
}

.solara-file-list .v-list-item-title {
  line-height: 28px;
}
</style>
