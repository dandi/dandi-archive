<template>
  <div>
    <v-card
      v-if="currentDandiset"
      height="100%"
      class="px-3 py-1 mb-3"
      outlined
    >
      <v-card-subtitle>
        Dandiset Actions
      </v-card-subtitle>

      <!-- Download, Shareable Link, and Cite As buttons -->
      <div class="mb-4">
        <v-row no-gutters>
          <DownloadDialog>
            <template
              #activator="{ on }"
              class="justify-left"
            >
              <v-btn
                id="download"
                outlined
                block
                v-on="on"
              >
                <v-icon
                  color="primary"
                  left
                >
                  mdi-download
                </v-icon>
                Download
                <v-spacer />
                <v-icon right>
                  mdi-chevron-down
                </v-icon>
              </v-btn>
            </template>
          </DownloadDialog>
        </v-row>
        <v-row no-gutters>
          <ShareableLinkDialog>
            <template
              #activator="{ on }"
              class="justify-left"
            >
              <v-btn
                id="download"
                outlined
                block
                v-on="on"
              >
                <v-icon
                  color="primary"
                  left
                >
                  mdi-link
                </v-icon>
                Shareable Link
                <v-spacer />
                <v-icon right>
                  mdi-chevron-down
                </v-icon>
              </v-btn>
            </template>
          </ShareableLinkDialog>
          <CiteAsDialog>
            <template
              #activator="{ on }"
              class="justify-left"
            >
              <v-btn
                id="download"
                outlined
                block
                v-on="on"
              >
                <v-icon
                  color="primary"
                  left
                >
                  mdi-format-quote-close
                </v-icon>
                Cite As
                <v-spacer />
                <v-icon right>
                  mdi-chevron-down
                </v-icon>
              </v-btn>
            </template>
          </CiteAsDialog>
        </v-row>
      </div>

      <!-- Files and Metadata buttons -->
      <div>
        <v-row no-gutters>
          <v-btn
            id="view-data"
            outlined
            block
            :to="fileBrowserLink"
          >
            <v-icon
              left
              color="primary"
            >
              mdi-folder
            </v-icon>
            Files
            <v-spacer />
          </v-btn>
        </v-row>
        <v-row no-gutters>
          <v-btn
            outlined
            style="width: 100%"
            @click="$emit('edit')"
          >
            <v-icon
              left
              color="primary"
            >
              mdi-note-text
            </v-icon>
            Metadata
            <v-spacer />
          </v-btn>
        </v-row>
      </div>
    </v-card>
    <v-card
      v-if="currentDandiset"
      height="100%"
      class="px-3 py-1"
      outlined
    >
      <v-row
        no-gutters
        class="my-1"
      >
        <v-card-subtitle>
          Ownership
        </v-card-subtitle>
        <DandisetOwners
          v-if="owners"
          :key="ownerDialogKey"
          :owners="owners"
          @close="ownerDialog = false"
        />
      </v-row>
    </v-card>
    <v-card
      outlined
      class="mt-4 pa-3"
    >
      <v-row
        class="mb-4"
        no-gutters
      >
        <template v-if="currentDandiset.version === 'draft'">
          <v-tooltip
            :disabled="!publishDisabledMessage"
            left
          >
            <template #activator="{ on }">
              <div
                style="width: 100%"
                v-on="on"
              >
                <v-btn
                  block
                  color="success"
                  :disabled="publishDisabled || !user"
                  @click="publish"
                >
                  Publish
                  <v-spacer />
                  <v-icon>mdi-upload</v-icon>
                </v-btn>
              </div>
            </template>
            <span>{{ publishDisabledMessage }}</span>
          </v-tooltip>
        </template>
      </v-row>

      <v-row
        class="mb-4"
        no-gutters
      >
        <v-menu
          v-if="currentDandiset.version_validation_errors.length"
          :nudge-width="200"
          offset-y
          open-on-hover
        >
          <template #activator="{ on: menu, attrs }">
            <v-tooltip bottom>
              <template #activator="{ on: tooltip }">
                <v-btn
                  block
                  class="amber lighten-5 no-text-transform"
                  depressed
                  v-bind="attrs"
                  v-on="{ ...tooltip, ...menu }"
                >
                  <v-icon
                    color="warning"
                    class="mr-1"
                  >
                    mdi-playlist-remove
                  </v-icon>
                  <v-spacer />
                  <span
                    style="white-space: normal"
                    class="text-caption"
                  >
                    This Dandiset has {{ currentDandiset.version_validation_errors.length }}
                    metadata<br>validation error(s).
                  </span>
                </v-btn>
              </template>
              <span>Fix issues with metadata</span>
            </v-tooltip>
          </template>
          <v-card class="pa-1">
            <v-list
              style="max-height: 200px"
              class="overflow-y-auto"
            >
              <div
                v-for="(error, index) in currentDandiset.version_validation_errors"
                :key="index"
              >
                <v-list-item>
                  <v-list-item-icon>
                    <v-icon>
                      {{ getValidationErrorIcon(error.field) }}
                    </v-icon>
                  </v-list-item-icon>

                  <v-list-item-content>
                    {{ error.field }}: {{ error.message }}
                  </v-list-item-content>
                </v-list-item>
                <v-divider />
              </div>
            </v-list>
            <v-btn
              color="primary"
              @click="$emit('edit')"
            >
              Fix issues
            </v-btn>
          </v-card>
        </v-menu>
      </v-row>

      <v-row
        class="mb-4"
        no-gutters
      >
        <v-menu
          v-if="currentDandiset.asset_validation_errors.length"
          :nudge-width="200"
          offset-y
          open-on-hover
        >
          <template #activator="{ on: menu, attrs }">
            <v-tooltip bottom>
              <template #activator="{ on: tooltip }">
                <v-btn
                  block
                  class="amber lighten-5 no-text-transform"
                  depressed
                  v-bind="attrs"
                  v-on="{ ...tooltip, ...menu }"
                >
                  <v-icon
                    color="warning"
                    class="mr-1"
                  >
                    mdi-database-remove
                  </v-icon>
                  <v-spacer />
                  <span
                    style="white-space: normal"
                    class="text-caption"
                  >
                    This Dandiset has {{ currentDandiset.asset_validation_errors.length }}
                    asset<br>validation error(s).
                  </span>
                </v-btn>
              </template>
              <span>Fix issues with assets</span>
            </v-tooltip>
          </template>
          <v-card class="pa-1">
            <v-list
              style="max-height: 200px"
              class="overflow-y-auto"
            >
              <div
                v-for="(error, index) in currentDandiset.asset_validation_errors"
                :key="index"
              >
                <v-list-item>
                  <v-list-item-icon>
                    <v-icon>
                      {{ getValidationErrorIcon(error.field) }}
                    </v-icon>
                  </v-list-item-icon>

                  <v-list-item-content>
                    {{ error.field }}: {{ error.message }}
                  </v-list-item-content>
                </v-list-item>
                <v-divider />
              </div>
            </v-list>
          </v-card>
        </v-menu>
      </v-row>
      <v-row>
        <v-subheader>
          This Version
        </v-subheader>
      </v-row>
      <v-row
        class="pa-2 mb-5 text-body-2 align-center"
        style="border-top: thin solid rgba(0, 0, 0, 0.12);
               border-bottom: thin solid rgba(0, 0, 0, 0.12);"
      >
        <v-col cols="5">
          {{ formatDate(currentDandiset.modified) }}
        </v-col>
        <v-col>
          <h3>{{ currentVersion.toUpperCase() }}</h3>
        </v-col>
      </v-row>
      <v-row>
        <v-subheader>
          Other Versions
        </v-subheader>
      </v-row>
      <v-row
        v-for="(version, i) in otherVersions.sort(sortVersions)"
        :key="i"
        class="pa-2 text-body-2 align-center"
        style="border-top: thin solid rgba(0, 0, 0, 0.12);
               border-bottom: thin solid rgba(0, 0, 0, 0.12);"
      >
        <v-col cols="5">
          {{ formatDate(version.modified) }}
        </v-col>
        <v-col>
          <v-btn
            outlined
            @click="setVersion(version)"
          >
            {{ version.version.toUpperCase() }}
          </v-btn>
        </v-col>
      </v-row>
    </v-card>
  </div>
</template>

<script lang="ts">
import {
  defineComponent, ref, computed, watch, Ref, ComputedRef,
} from '@vue/composition-api';

import moment from 'moment';

import { publishRest, loggedIn as loggedInFunc, user as userFunc } from '@/rest';
import { User, Version } from '@/types';

import { draftVersion, VALIDATION_ICONS } from '@/utils/constants';
import { RawLocation } from 'vue-router';
import DandisetOwners from './DandisetOwners.vue';
import DownloadDialog from './DownloadDialog.vue';
import ShareableLinkDialog from './ShareableLinkDialog.vue';
import CiteAsDialog from './CiteAsDialog.vue';

function getValidationErrorIcon(errorField: string): string {
  const icons = Object.keys(VALIDATION_ICONS).filter((field) => errorField.includes(field));
  if (icons.length > 0) {
    return (VALIDATION_ICONS as any)[icons[0]];
  }
  return VALIDATION_ICONS.DEFAULT;
}

// Sort versions from most recently modified to least recently modified.
// The DRAFT version is always the first element when present.
function sortVersions(v1: Version, v2: Version) {
  // Always put draft first
  if (v1.version === 'draft' || v1.modified > v2.modified) {
    return -1;
  }
  if (v1.modified < v2.modified) {
    return 1;
  }
  return 0;
}

export default defineComponent({
  name: 'DandisetDetails',
  components: {
    CiteAsDialog,
    DandisetOwners,
    DownloadDialog,
    ShareableLinkDialog,
  },
  props: {
    userCanModifyDandiset: {
      type: Boolean,
      required: true,
    },
  },
  setup(props, ctx) {
    const { userCanModifyDandiset } = props;

    const store = ctx.root.$store;

    const currentDandiset: ComputedRef<Version> = computed(
      () => store.state.dandiset.publishDandiset,
    );
    const owners: ComputedRef<User[]> = computed(() => store.state.dandiset.owners);

    const currentVersion: ComputedRef<string> = computed(
      () => store.getters['dandiset/version'],
    );

    const otherVersions: ComputedRef<Version[]> = computed(
      () => store.state.dandiset.versions.filter(
        (version: Version) => version.version !== currentVersion.value,
      ),
    );

    const user: ComputedRef<any> = computed(userFunc);
    const loggedIn: ComputedRef<boolean> = computed(loggedInFunc);

    const publishDisabledMessage: ComputedRef<string> = computed(() => {
      if (!loggedIn.value) {
        return 'You must be logged in to edit.';
      }
      if (!userCanModifyDandiset) {
        return 'You do not have permission to edit this dandiset.';
      }
      if (currentDandiset.value.status === 'Pending') {
        return 'This dandiset has not yet been validated.';
      }
      if (currentDandiset.value.status === 'Validating') {
        return 'Currently validating this dandiset.';
      }
      if (currentDandiset.value.status === 'Published') {
        return 'No changes since last publish.';
      }
      return '';
    });

    const publishDisabled: ComputedRef<boolean> = computed(
      () => !!(currentDandiset.value.version_validation_errors.length
        || currentDandiset.value.asset_validation_errors.length
        || publishDisabledMessage.value),
    );

    const stats: Ref<any> = ref(null);
    watch(currentDandiset, async () => {
      if (currentDandiset.value) {
        const { asset_count, size } = currentDandiset.value;
        stats.value = { asset_count, size };
      }
    }, { immediate: true });

    const ownerDialog: Ref<boolean> = ref(false);
    const ownerDialogKey: Ref<number> = ref(0);

    function formatDate(date: string) {
      return moment(date).format('MM/DD/YYYY');
    }

    const fileBrowserLink: ComputedRef<any> = computed(() => {
      const version = currentVersion.value;
      const { identifier } = currentDandiset.value.dandiset;
      return {
        name: 'fileBrowser',
        params: { identifier, version },
        query: {
          location: '',
        },
      };
    });

    function setVersion({ version: newVersion }: any) {
      const version = newVersion || draftVersion;

      if (ctx.root.$route.params.version !== version) {
        ctx.root.$router.replace({
          ...ctx.root.$route,
          params: {
            ...ctx.root.$route.params,
            version,
          },
        } as RawLocation);

        store.dispatch('dandiset/fetchPublishDandiset', { identifier: currentDandiset.value.dandiset.identifier, version: newVersion });
      }
    }

    async function publish() {
      const version = await publishRest.publish(currentDandiset.value.dandiset.identifier);
      // re-initialize the dataset to load the newly published version
      await store.dispatch('dandiset/initializeDandisets', { identifier: currentDandiset.value.dandiset.identifier, version: version.version });
    }

    function timelineVersionItemColor(version: Version): string {
      if (currentDandiset.value && version.version === currentDandiset.value.version) { return 'primary'; }
      if (!currentDandiset.value && version.version === draftVersion) {
        return 'amber darken-4';
      }

      return 'grey';
    }

    return {
      ownerDialog,
      ownerDialogKey,
      currentDandiset,
      owners,
      currentVersion,
      otherVersions,
      stats,
      setVersion,
      timelineVersionItemColor,
      formatDate,
      fileBrowserLink,
      sortVersions,
      user,
      publishDisabledMessage,
      publishDisabled,
      getValidationErrorIcon,
      publish,
    };
  },
});
</script>
