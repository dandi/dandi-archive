<template>
  <v-btn
    icon
    :disabled="!loggedIn"
    @click="toggleStar"
  >
    <v-icon :color="isStarred ? 'amber darken-2' : undefined">
      {{ isStarred ? 'mdi-star' : 'mdi-star-outline' }}
    </v-icon>
    <span class="ml-1">{{ starCount }}</span>
  </v-btn>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { dandiRest, loggedIn as loggedInFunc } from '@/rest';

const props = defineProps<{
  identifier: string;
  initialStarCount: number;
  initialIsStarred: boolean;
}>();

const loggedIn = computed(loggedInFunc);
const isStarred = ref(props.initialIsStarred);
const starCount = ref(props.initialStarCount);

async function toggleStar() {
  try {
    if (isStarred.value) {
      await dandiRest.unstarDandiset(props.identifier);
      starCount.value--;
    } else {
      await dandiRest.starDandiset(props.identifier);
      starCount.value++;
    }
    isStarred.value = !isStarred.value;
  } catch (error) {
    console.error('Error toggling star:', error);
  }
}
</script> 