<template>
  <div>
    <div
      v-for="(row, index) in modelValue"
      :key="index"
      class="d-flex align-start mb-1"
    >
      <div class="flex-grow-1">
        <slot
          :row="row"
          :index="index"
        />
      </div>
      <v-btn
        icon="mdi-close"
        variant="text"
        size="small"
        class="ml-1 mt-1"
        :aria-label="`Remove ${itemLabel}`"
        @click="remove(index)"
      />
    </div>
    <v-btn
      prepend-icon="mdi-plus"
      variant="text"
      color="primary"
      size="small"
      @click="add"
    >
      Add {{ itemLabel }}
    </v-btn>
  </div>
</template>

<script setup lang="ts" generic="T">
// A list of editable rows with add and remove controls. Rows are objects
// owned by the parent; slot content binds directly to their fields.
const props = defineProps<{
  modelValue: T[];
  blank: () => T;
  itemLabel: string;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: T[]): void;
}>();

function add() {
  emit('update:modelValue', [...props.modelValue, props.blank()]);
}

function remove(index: number) {
  emit('update:modelValue', props.modelValue.filter((_, i) => i !== index));
}
</script>
