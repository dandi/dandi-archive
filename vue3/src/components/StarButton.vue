<template>
  <div>
    <v-btn icon :disabled="!loggedIn" @click.prevent="toggleStar">
      <v-icon :color="isStarred ? 'amber darken-2' : undefined">
        {{ isStarred ? 'mdi-star' : 'mdi-star-outline' }}
      </v-icon>
    </v-btn>
    <span class="ml-1 text-button">{{ starCount }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, toRefs } from 'vue';
import { dandiRest, loggedIn as loggedInFunc } from '@/rest';

const props = defineProps<{
  identifier: string;
  initialStarCount: number;
  initialIsStarred: boolean;
}>();
const { initialIsStarred, initialStarCount } = toRefs(props)
const loggedIn = computed(loggedInFunc);
const offset = ref(0);
const starCount = computed(() => initialStarCount.value + offset.value);
const isStarred = computed(() => (initialIsStarred.value && offset.value === 0) || (!initialIsStarred.value && offset.value === 1));

async function toggleStar() {
  try {
    if (isStarred.value) {
      await dandiRest.unstarDandiset(props.identifier);
      offset.value -= 1;
    } else {
      await dandiRest.starDandiset(props.identifier);
      offset.value += 1;
    }
  } catch (error) {
    console.error('Error toggling star:', error);
  }
}
</script>