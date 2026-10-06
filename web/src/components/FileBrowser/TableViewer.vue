<!--
  Opens the table viewer for whichever of `items` the URL names, and closes it
  when the URL stops naming one. Keeping the state in the URL means the file
  browser needs to know nothing about the viewer beyond linking to it (see
  tableViewer.ts), so dropping the feature is a matter of removing this
  component and that link.
-->
<template>
  <TableViewerDialog
    :model-value="!!item"
    :item="item"
    :identifier="identifier"
    :version="version"
    @update:model-value="$event ? undefined : close()"
  />
</template>

<script setup lang="ts">
import type { Ref } from 'vue';
import { computed, ref, watchEffect } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import { useRoute, useRouter } from 'vue-router';

import type { AssetPath } from '@/types';
import TableViewerDialog from '@/components/FileBrowser/TableViewerDialog.vue';
import { TABLE_QUERY_PARAM, firstQueryValue, viewableAsTable } from '@/components/FileBrowser/tableViewer';

const props = defineProps<{
  items: AssetPath[] | null,
  identifier: string,
  version: string,
}>();

const route = useRoute();
const router = useRouter();

const targetPath = computed(() => firstQueryValue(route.query[TABLE_QUERY_PARAM]));
const item: Ref<AssetPath | null> = ref(null);

watchEffect(() => {
  const path = targetPath.value;
  if (!path) {
    item.value = null;
    return;
  }
  // The listing can be refetched while the viewer is open, which replaces every
  // item object. Holding on to the one already open keeps the viewer from
  // reloading the file underneath the user.
  if (item.value?.path === path) {
    return;
  }
  // The viewer can only be opened once the item the URL names has been loaded.
  item.value = props.items?.find(
    (candidate) => candidate.path === path && viewableAsTable(candidate),
  ) || null;
});

function close() {
  // Opening the viewer pushes a history entry, so closing it goes back, leaving
  // the browser's back button on the entry the user came from rather than on the
  // open viewer. A link straight into the viewer has nothing to go back to, so
  // that case drops the query parameter instead.
  const { back } = router.options.history.state;
  if (typeof back === 'string' && !back.includes(`${TABLE_QUERY_PARAM}=`)) {
    router.back();
    return;
  }

  const query = { ...route.query };
  delete query[TABLE_QUERY_PARAM];
  router.replace({ ...route, query } as RouteLocationRaw);
}
</script>
