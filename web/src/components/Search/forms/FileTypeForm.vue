<script setup lang="ts">
import { searchParameters } from "../store";

const FILE_TYPES = ["application/x-nwb", "image/", "video/", "text/"];
</script>

<template>
  <v-select
    v-model="searchParameters.file_type"
    multiple
    outlined
    :items="FILE_TYPES"
    label="File type(s)"
  />
</template>
