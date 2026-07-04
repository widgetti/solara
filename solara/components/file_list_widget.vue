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
          @click.stop="clicked = { name, is_file }"
          @dblclick="double_clicked = { name, is_file }"
          :class="['solara-file-list-item', (clicked && clicked.name == name) ? 'solara-file-list-selected': '']"
      >
        <div class="solara-file-list-row">
          <div class="solara-file-list-icon">
            <v-icon>{{ name === '..' ? 'mdi-keyboard-backspace' : is_file ? 'mdi-file-document' : 'mdi-folder' }}</v-icon>
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
  mounted() {
    const element = this.$refs.scrollpane.$el
    element.scrollTop = this.scroll_pos

    this._scrollListener = _.debounce((e) => {
      this.scroll_pos = Math.round(element.scrollTop)
    }, 50)
    element.addEventListener('scroll', this._scrollListener)
  },
  watch: {
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
