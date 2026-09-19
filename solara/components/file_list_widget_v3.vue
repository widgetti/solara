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
      click_id: 0,
      // Match the Vue 2 template: update highlighting before the Python round trip.
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
