<template>
  <div :style="`overflow: auto; ${style_}`">
    <h4>{{d.agg}}</h4>
      <div style="padding: 0px">
      <table class="pivottable">
        <tr v-for="(header, i) in d.headers_x">
          <th v-for="axis in Math.max(0, d.y.length-1)"></th>
          <th>{{d.x[i]}}</th>
          <th v-for="(label, col) in header" @click="select({x: [i, col]})" :class="{'selected': isSelected2({x: [i, col]}), 'clickable': true}">
            {{col == 0 ? header[col] : header[col] == header[col-1] ? '' : header[col]}}
          </th>
          <th v-if="i == d.headers_x.length - 1">Total </th>
        </tr>
        <tr>
          <th v-for="axis in d.y"> {{axis}}</th>
        </tr>
        <tr v-for="row in rowIndex">
          <th v-for="(header, yi) in d.headers_y" @click="select({y: [yi, row]})" :class="{'selected': isSelected2({y: [yi, row]}), 'clickable': true}">
            {{row == 0 ? header[row] : header[row] == header[row-1] ? '' : header[row]}}
          </th>
          <td v-for="col in colIndex"
             :class="{'selected': isSelected2({y: [d.headers_y.length-1, row], x: [d.headers_x.length-1, col]}), 'clickable': true}"
             @click="select({y: [d.headers_y.length-1, row], x: [d.headers_x.length-1, col]})"
          >
            {{d.values[col][row]}}
          </td>
          <td>
            {{d.values_y[row]}}
          </td>
        </tr>

        <tr>
          <th>Total </td>
          <th v-for="axis in Math.max(0, d.y.length-1)"></th>
          <td v-for="value in d.values_x">{{value}} </td>
          <td>
            {{d.total}}
          </td>
        </tr>
      </table>
      </div>
  </div>
</div>
</template>

<script id="pivottable-vaex">
module.exports = {
  computed: {
    rowIndex() {
      return [...Array(this.d.counts_y).keys()];
    },
    colIndex() {
      return [...Array(this.d.counts_x).keys()];
    },
  },
  methods: {
    select(values) {
      console.log(values, this.selected);
      if (_.isEqual(values, this.selected)) {
        this.selected = {};
      } else {
        this.selected = values;
      }
    },
    levelValue(axis, levels, index) {
      values = [];
      for (let level = 0; level < levels + 1; level++) {
        values.push(this.d[`headers_${axis}`][level][index]);
      }
      // console.log(values)
      return values;
    },
    isSelected2(values) {
      selected_value = selected = true;
      if (_.isEqual(this.selected, {})) {
        return false;
      }
      console.log(values);
      if (values) {
        // if('x' in values && 'x' in this.selected) {
        if ("x" in this.selected) {
          if ("x" in values) {
            const levelsSelected = this.selected.x[0];
            const indexSelected = this.selected.x[1];
            const levelsCurrent = Math.min(levelsSelected, values.x[0]);
            const indexCurrent = values.x[1];
            const currentValue = this.levelValue(
              "x",
              levelsCurrent,
              indexCurrent
            );
            const selectedValue = this.levelValue(
              "x",
              levelsSelected,
              indexSelected
            );
            console.log("selectedValue", currentValue, selectedValue);
            selected &= _.isEqual(currentValue, selectedValue);
          } else {
            selected = false;
          }
        }
        if ("y" in this.selected) {
          if ("y" in values) {
            const levelsSelected = this.selected.y[0];
            const indexSelected = this.selected.y[1];
            const levelsCurrent = Math.min(levelsSelected, values.y[0]);
            const indexCurrent = values.y[1];
            const currentValue = this.levelValue(
              "y",
              levelsCurrent,
              indexCurrent
            );
            const selectedValue = this.levelValue(
              "y",
              levelsSelected,
              indexSelected
            );
            console.log("selectedValue", currentValue, selectedValue);
            selected &= _.isEqual(currentValue, selectedValue);
          } else {
            selected = false;
          }
        } else if (!("y" in values)) {
          // selected = false;
        }
      }
      return selected;
    },
  },
};
</script>

<style id="pivottable-vaex">
.pivottable th,
.pivottable td {
  padding: 10px;
  text-align: end;
}
.pivottable .clickable {
  cursor: pointer;
}
.pivottable td.clickable {
  /* font-weight: 500; */
  text-decoration: underline;
}
.pivottable th {
  border-bottom: 1px solid #ccc;
}

.pivottable td {
  border-bottom: 1px solid #eee;
}

.pivottable .selected {
  background-color: #eee;
}
</style>
