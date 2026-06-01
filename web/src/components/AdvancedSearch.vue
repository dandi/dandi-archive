<template>
  <div>
    <!-- Search Input -->
    <v-text-field
      v-model="searchQuery"
      label="Search"
      prepend-inner-icon="mdi-magnify"
      clearable
      @update:model-value="onSearch"
    >
      <template #append>
        <v-btn
          icon
          variant="text"
          @click="showAdvanced = !showAdvanced"
        >
          <v-icon>{{ showAdvanced ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
        </v-btn>
      </template>
    </v-text-field>

    <!-- Active Filters Display -->
    <v-chip-group
      v-if="hasActiveFilters"
      class="mb-3"
    >
      <v-chip
        v-if="filters.published_after"
        closable
        @click:close="clearFilter('published_after')"
      >
        Published after: {{ formatDate(filters.published_after) }}
      </v-chip>
      <v-chip
        v-for="license in filters.license"
        :key="license"
        closable
        @click:close="removeLicense(license)"
      >
        License: {{ license }}
      </v-chip>
      <v-chip
        v-if="filters.species"
        closable
        @click:close="clearFilter('species')"
      >
        Species: {{ filters.species }}
      </v-chip>
      <v-chip
        v-for="type in filters.file_type"
        :key="type"
        closable
        @click:close="removeFileType(type)"
      >
        File type: {{ type }}
      </v-chip>
      <v-chip
        v-if="filters.file_size_min || filters.file_size_max"
        closable
        @click:close="clearSizeFilters"
      >
        Size: {{ formatSizeRange }}
      </v-chip>
      <v-chip
        v-for="technique in filters.measurement_technique"
        :key="technique"
        closable
        @click:close="removeTechnique(technique)"
      >
        Technique: {{ technique }}
      </v-chip>
    </v-chip-group>

    <!-- Advanced Search Panel -->
    <v-expand-transition>
      <div
        v-if="showAdvanced"
        class="advanced-search-panel"
      >
        <v-card
          class="mb-4 pa-4"
          style="position: relative; z-index: 1;"
        >
          <v-row>
            <!-- Date Filter -->
            <v-col
              cols="12"
              md="4"
            >
              <v-menu
                ref="dateMenu"
                v-model="dateMenu"
                :close-on-content-click="false"
                transition="scale-transition"
                offset-y
                max-width="290px"
                min-width="auto"
              >
                <template #activator="{ props }">
                  <v-text-field
                    v-model="filters.published_after"
                    label="Published After"
                    persistent-hint
                    prepend-icon="mdi-calendar"
                    v-bind="props"
                    readonly
                  />
                </template>
                <v-date-picker
                  v-model="filters.published_after"
                  @update:model-value="dateMenu = false"
                />
              </v-menu>
            </v-col>

            <!-- License Filter -->
            <v-col
              cols="12"
              md="4"
            >
              <v-select
                v-model="filters.license"
                :items="licenseOptions"
                label="License"
                multiple
                chips
                clearable
              />
            </v-col>

            <!-- Species Filter -->
            <v-col
              cols="12"
              md="4"
            >
              <v-text-field
                v-model="filters.species"
                label="Species"
                clearable
                hint="Enter species name or NCBI Taxonomy ID"
                persistent-hint
              />
            </v-col>

            <!-- File Type Filter -->
            <v-col
              cols="12"
              md="4"
            >
              <v-select
                v-model="filters.file_type"
                :items="fileTypeOptions"
                label="File Type"
                multiple
                chips
                clearable
              />
            </v-col>

            <!-- File Size Filter -->
            <v-col
              cols="12"
              md="4"
            >
              <v-text-field
                v-model.number="filters.file_size_min"
                label="Min Size (bytes)"
                type="number"
                clearable
              />
            </v-col>
            <v-col
              cols="12"
              md="4"
            >
              <v-text-field
                v-model.number="filters.file_size_max"
                label="Max Size (bytes)"
                type="number"
                clearable
              />
            </v-col>

            <!-- Measurement Technique Filter -->
            <v-col cols="12">
              <v-select
                v-model="filters.measurement_technique"
                :items="techniqueOptions"
                label="Measurement Technique"
                multiple
                chips
                clearable
              />
            </v-col>
          </v-row>

          <!-- Filter Actions -->
          <v-row class="mt-2">
            <v-col class="text-right">
              <v-btn
                color="primary"
                variant="text"
                @click="clearAllFilters"
              >
                Clear All Filters
              </v-btn>
              <v-btn
                color="primary"
                class="ml-2"
                @click="applyFilters"
              >
                Apply Filters
              </v-btn>
            </v-col>
          </v-row>
        </v-card>
      </div>
    </v-expand-transition>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, computed } from 'vue';
import moment from 'moment';
import filesize from 'filesize';

interface Filters {
  published_after: string | null;
  license: Array<string>;
  species: string | null;
  file_type: Array<string>;
  file_size_min: number | null;
  file_size_max: number | null;
  measurement_technique: Array<string>;
}

export default defineComponent({
  name: 'AdvancedSearch',
  emits: ['search'],

  setup(props, { emit }) {
    const searchQuery = ref('');
    const showAdvanced = ref(false);
    const dateMenu = ref(false);

    const filters = ref<Filters>({
      published_after: null,
      license: [],
      species: null,
      file_type: [],
      file_size_min: null,
      file_size_max: null,
      measurement_technique: [],
    });

    const licenseOptions = [
      'CC0',
      'CC-BY-4.0',
      'CC-BY-NC-4.0',
    ];

    const fileTypeOptions = [
      'application/x-nwb',
      'image/',
      'text/',
      'video/',
    ];

    const techniqueOptions = [
      'signal filtering technique',
      'spike sorting technique',
      'multi electrode extracellular electrophysiology recording technique',
      'voltage clamp technique',
      'surgical technique',
      'behavioral technique',
      'current clamp technique',
      'fourier analysis technique',
      'two-photon microscopy technique',
      'patch clamp technique',
      'analytical technique',
    ];

    const hasActiveFilters = computed(() => {
      return (
        !!filters.value.published_after ||
        filters.value.license.length > 0 ||
        !!filters.value.species ||
        filters.value.file_type.length > 0 ||
        !!filters.value.file_size_min ||
        !!filters.value.file_size_max ||
        filters.value.measurement_technique.length > 0
      );
    });

    const formatSizeRange = computed(() => {
      const { file_size_min, file_size_max } = filters.value;
      if (file_size_min && file_size_max) {
        return `${filesize(file_size_min)} - ${filesize(file_size_max)}`;
      }
      if (file_size_min) {
        return `>= ${filesize(file_size_min)}`;
      }
      if (file_size_max) {
        return `<= ${filesize(file_size_max)}`;
      }
      return '';
    });

    function formatDate(date: string) {
      return moment(date).format('LL');
    }

    function clearFilter(key: keyof Filters) {
      const value = filters.value[key];
      if (Array.isArray(value)) {
        if (key === 'license') filters.value.license = [];
        if (key === 'file_type') filters.value.file_type = [];
        if (key === 'measurement_technique') filters.value.measurement_technique = [];
      } else {
        if (key === 'published_after') filters.value.published_after = null;
        if (key === 'species') filters.value.species = null;
        if (key === 'file_size_min') filters.value.file_size_min = null;
        if (key === 'file_size_max') filters.value.file_size_max = null;
      }
      applyFilters();
    }

    function removeLicense(license: string) {
      filters.value.license = filters.value.license.filter(l => l !== license);
      applyFilters();
    }

    function removeFileType(type: string) {
      filters.value.file_type = filters.value.file_type.filter(t => t !== type);
      applyFilters();
    }

    function removeTechnique(technique: string) {
      filters.value.measurement_technique = filters.value.measurement_technique.filter(t => t !== technique);
      applyFilters();
    }

    function clearSizeFilters() {
      filters.value.file_size_min = null;
      filters.value.file_size_max = null;
      applyFilters();
    }

    function clearAllFilters() {
      filters.value = {
        published_after: null,
        license: [],
        species: null,
        file_type: [],
        file_size_min: null,
        file_size_max: null,
        measurement_technique: [],
      };
      applyFilters();
    }

    function onSearch() {
      applyFilters();
    }

    function applyFilters() {
      const searchParams: Record<string, any> = {};

      // Add text search if present
      if (searchQuery.value) {
        searchParams.q = searchQuery.value;
      }

      // Add filters if they have values
      if (filters.value.published_after) {
        searchParams.published_after = filters.value.published_after;
      }
      if (filters.value.license.length) {
        searchParams.license = filters.value.license;
      }
      if (filters.value.species) {
        searchParams.species = filters.value.species;
      }
      if (filters.value.file_type.length) {
        searchParams.file_type = filters.value.file_type;
      }
      if (filters.value.file_size_min !== null) {
        searchParams.file_size_min = filters.value.file_size_min;
      }
      if (filters.value.file_size_max !== null) {
        searchParams.file_size_max = filters.value.file_size_max;
      }
      if (filters.value.measurement_technique.length) {
        searchParams.measurement_technique = filters.value.measurement_technique;
      }

      emit('search', searchParams);
    }

    return {
      searchQuery,
      showAdvanced,
      dateMenu,
      filters,
      licenseOptions,
      fileTypeOptions,
      techniqueOptions,
      hasActiveFilters,
      formatSizeRange,
      formatDate,
      clearFilter,
      removeLicense,
      removeFileType,
      removeTechnique,
      clearSizeFilters,
      clearAllFilters,
      onSearch,
      applyFilters,
    };
  },
});
</script>

<style>
.advanced-search-panel {
  position: relative;
}

.v-menu__content {
  position: fixed !important;
  z-index: 7 !important;
}

.advanced-search-panel .v-card {
  margin-top: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
}

/* Override Vuetify's default z-index for date picker */
.v-picker__body {
  z-index: 7 !important;
}
</style>
