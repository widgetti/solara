<template>
  <v-slide-x-transition appear>
    <div class="solara-data-table__viewport">
      <v-data-table dense hide-default-header :headers="[...headers]" :items="items"
        :footer-props="{ 'items-per-page-options': [10, 20, 50, 100] }" :options.sync="options"
        :items_per_page.sync="items_per_page" :server-items-length="total_length" :class="[
          'elevation-1',
          'solara-data-table',
          scrollable && 'solara-data-table--scrollable',
        ]" :style="scrollable && height != null && `height: ${height}`">
        <template v-slot:header="props">
          <thead>
            <tr>
              <th style="padding: 0 10px; width: 40px">#</th>
              <th style="padding: 0 1px; width: 30px" v-if="selection_enabled">
                <v-btn icon color="primary" text small @click="apply_filter">
                  <v-icon>filter_list</v-icon>
                </v-btn>
              </th>
              <th style="padding: 0 1px" v-for="(header, index) in headers_selections" :key="header.text">
                <v-icon style="padding: 0 1px" :key="index" :color="selection_colors[index]">brightness_1</v-icon>
              </th>
              <v-slide-x-transition :key="header.text" v-for="header in headers">
                <th class="text-no-wrap">
                  {{ header.text }}
                  <v-menu open-on-hover bottom offset-y @input="isOpen => onHeaderHover({ isOpen, header })"
                    v-if="(column_actions && column_actions.length) || column_header_widget">
                    <template v-slot:activator="{ on, attrs }">
                      <v-icon v-bind="attrs" v-on="on" small class="solara-data-table-menu">mdi-dots-vertical</v-icon>
                    </template>
                    <v-sheet v-if="header.value === column_header_hover" class="solara-data-table-column-header-sheet">
                      <jupyter-widget v-if="column_header_widget" :widget="column_header_widget"></jupyter-widget>
                    </v-sheet>
                    <v-list v-if="column_actions && column_actions.length">
                      <v-subheader>Actions:</v-subheader>
                      <v-list-item link @click="on_column_action([header.value, index])"
                        v-for="(action, index) in column_actions" :key="index">
                        <v-list-item-icon><v-icon>{{ action.icon }}</v-icon></v-list-item-icon>
                        <v-list-item-title>{{ action.name }}</v-list-item-title>
                      </v-list-item>
                    </v-list>
                  </v-menu>
                </th>
              </v-slide-x-transition>
            </tr>
          </thead>
        </template>
        <template v-slot:item="props">
          <!-- @click="on_row_clicked(props.item.__row__)" -->
          <tr :class="{ highlightedRow: props.item.__row__ === highlighted }">
            <td style="padding: 0 10px" class="text-xs-left">
              <i>{{ props.item.__row__ }}</i>
            </td>
            <td style="padding: 0 1px" class="text-xs-left" v-if="selection_enabled">
              <v-checkbox hide-details style="margin-top: 0; padding-top: 0"
                :input-value="checked.indexOf(props.item.__row__) != -1" :key="props.item.__row__"
                @change="(value) => select({ checked: value, row: props.item.__row__ })" />
            </td>
            <td style="padding: 0 1px" :key="header.text" v-for="(header, index) in headers_selections">
              <v-fade-transition leave-absolute>
                <v-icon v-if="props.item[header.value]" v-model="props.item[header.value]"
                  :color="selection_colors[index]">brightness_1</v-icon>
              </v-fade-transition>
            </td>
            <td v-for="header in headers" class="text-truncate text-no-wrap" :key="header.text"
              :title="props.item[header.value]">
              <v-slide-x-transition appear>
                <!-- <span @click="on_item_click([props.item.__row__, header.value])">{{ props.item[header.value] }}</span> -->
                <span>
                  {{ props.item[header.value] }}
                  <v-menu open-on-hover bottom offset-y v-if="cell_actions.length">
                    <template v-slot:activator="{ on, attrs }">
                      <v-icon v-bind="attrs" v-on="on" small class="solara-data-table-menu">mdi-dots-vertical</v-icon>
                    </template>
                    <v-list v-for="(action, index) in cell_actions" :key="index">
                      <v-list-item link @click="on_cell_action([props.item.__row__, header.value, index])">
                        <v-list-item-icon><v-icon>{{ action.icon }}</v-icon></v-list-item-icon>
                        <v-list-item-title>{{ action.name }}</v-list-item-title>
                      </v-list-item>
                    </v-list>
                  </v-menu>
                </span>

              </v-slide-x-transition>
            </td>
          </tr>
        </template>
      </v-data-table>
    </div>
  </v-slide-x-transition>
</template>

<script>
module.exports = {
  methods: {
    onHeaderHover({ header, isOpen }) {
      if (isOpen) {
        // if isOpen is true, we clicked, and we set it header.value
        this.column_header_hover = header.value
      } else {
        // if false, we only 'unset' if the current header equals the current open menu
        // because sometimes the menu from another column is closed after opening the new one
        if (this.column_header_hover == header.value) {
          this.column_header_hover = null
        }
      }
    }
  }
}
</script>
<style id="solara_table">
.highlightedRow {
  background-color: #e3f2fd;
}

.solara-data-table table {
  table-layout: fixed;
}

.solara-data-table--scrollable .v-data-table__wrapper {
  overflow-y: auto;
  height: calc(100% - 59px);
}

.solara-data-table--scrollable thead>tr {
  position: sticky;
  top: 0;
}

.solara-data-table--scrollable .v-data-table__wrapper,
.solara-data-table--scrollable .v-data-table__wrapper>table,
.solara-data-table--scrollable .v-data-table__wrapper>table thead,
.solara-data-table--scrollable .v-data-table__wrapper>table thead * {
  background-color: inherit;
}

/* prevent checkboxes overlaying the table header */
.solara-data-table--scrollable .v-data-table__wrapper>table thead {
  position: relative;
  z-index: 1;
}

/* avoid margins to collapse, to avoid a white background */
.solara-data-table-column-header-sheet {
  overflow: auto;
}

.solara-data-table.v-data-table th,
.solara-data-table.v-data-table td {
  padding-left: 4px;
  padding-right: 0;
}

.v-data-table .solara-data-table-menu {
  opacity: 0;
  transition: opacity 0.5s;
}

.v-data-table th:hover .solara-data-table-menu,
.v-data-table td:hover .solara-data-table-menu {
  opacity: 1;
}

.solara-data-table__viewport {
  overflow-x: auto;
  width: 100%;
  max-height: 100%;
}

.solara-data-table.v-data-table,
.solara-data-table.v-data-table table {
  max-width: unset;
  width: unset;
}
</style>
