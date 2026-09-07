<template>
  <v-card v-page-title="'Create Dandiset'">
    <v-card-title>
      <span class="text-h3">Register a new Dandiset</span>
    </v-card-title>
    <v-card-text class="my-3">
      <v-form>
        <div>
          <v-switch
            v-model="embargoed"
          >
            <template #label>
              Embargo this Dandiset
              <v-tooltip
                location="right"
                width="30vw"
              >
                <template #activator="{ props }">
                  <div
                    style="cursor: help"
                    v-bind="props"
                  >
                    <small class="ml-3 d-flex align-center">
                      (What is this?)
                      <v-icon size="small">
                        mdi-information
                      </v-icon>
                    </small>
                  </div>
                </template>
                <span>
                  Embargoed Dandisets are hidden from public access until a specific time period has
                  elapsed. You can associate the dandiset with a research award/grant or set a
                  2-year embargo period. The data will be automatically published when the embargo
                  period expires.
                </span>
              </v-tooltip>
            </template>
          </v-switch>
        </div>
        <div class="text-h4">
          Title
        </div>
        <div>
          The title appears in search results and at the top of the landing page
          for this Dandiset. It should be about as descriptive as the title of a
          journal article: say what was recorded, in which species and brain
          region, and under what conditions. If this Dandiset accompanies a
          specific paper or preprint, you may reuse that title.
        </div>
        <v-text-field
          v-model="name"
          label="Title"
          :placeholder="titlePlaceholder"
          :counter="nameMaxLength"
          required
          variant="outlined"
          density="compact"
          class="my-4"
        />
        <v-alert
          v-if="showShortTitleHint"
          type="info"
          variant="tonal"
          class="my-2"
        >
          This title is quite short. Titles that read like a journal article title
          (for example, "{{ titlePlaceholder }}") are much easier for other
          researchers to find and understand.
        </v-alert>
        <v-alert
          v-if="showTestWarning"
          type="warning"
          variant="tonal"
          class="my-2"
        >
          <span>
            If this is a test dandiset and does not contain actual neuroscience data,
            please consider using the sandbox instance instead. See documentation
            <a
              :href="sandboxDocsUrl"
              target="_blank"
            >here</a>
            for how to use the the sandbox instance.
          </span>
        </v-alert>

        <div class="text-h4">
          Description
        </div>
        <div>
          The description appears prominently under the title on the landing
          page and is the main text other researchers will use to decide whether
          this data is useful to them. You may paste the abstract of the
          associated paper, and you are encouraged to go further. A good
          description covers:
          <ul class="my-2 ml-6">
            <li>the scientific question or purpose of the experiment</li>
            <li>the species, number of subjects, and brain regions studied</li>
            <li>the recording techniques used (e.g. Neuropixels, two-photon calcium imaging, patch clamp)</li>
            <li>the behavioral task or stimulus paradigm, if any</li>
            <li>how the data are organized and what each file contains</li>
          </ul>
          Markdown formatting is supported.
        </div>
        <v-textarea
          v-model="description"
          label="Description"
          :placeholder="descriptionPlaceholder"
          :counter="descriptionMaxLength"
          required
          variant="outlined"
          density="compact"
          class="my-4"
        />
        <v-alert
          v-if="showShortDescriptionHint"
          type="info"
          variant="tonal"
          class="my-2"
        >
          This description is quite short. Consider adding the details listed
          above so that others can understand what this Dandiset contains
          without opening the files.
        </v-alert>
        <div v-if="!embargoed">
          <div class="text-h4">
            License
          </div>
          <div>
            Select a license under which to share the contents of this Dandiset.
            You can learn more about <a
              :href="`${dandiDocumentationUrl}/user-guide-sharing/data-licenses`"
              target="_blank"
              rel="noopener"
            >
              licenses for Dandisets
            </a>.
          </div>
          <v-select
            v-model="license"
            :items="dandiLicenses"
            label="License"
            data-testid="license-select"
            class="my-4"
            variant="outlined"
            density="compact"
          />
        </div>
        <div v-else>
          <div class="text-h4">
            Award Information
          </div>
          <div>
            <v-switch
              v-model="hasAward"
              class="mb-4"
            >
              <template #label>
                This Dandiset is associated with a research award/grant
              </template>
            </v-switch>
          </div>

          <div v-if="hasAward">
            <div class="text-h5 mb-2">
              Funding Source
            </div>
            <div class="mb-3">
              Specify the funding organization for this research. It will be
              listed as a funder of this Dandiset.
            </div>
            <v-text-field
              v-model="fundingSource"
              label="Funding source (e.g., National Institutes of Health)"
              required
              variant="outlined"
              density="compact"
              class="mb-4"
              :rules="fundingSourceRules"
            />

            <div class="text-h5 mb-2">
              Grant/Award Number
            </div>
            <div class="mb-3">
              Provide the grant or award number. For awards without a grant number, please
              provide the project name.
            </div>
            <v-text-field
              v-model="awardNumber"
              label="Grant/Award number"
              :counter="120"
              required
              variant="outlined"
              density="compact"
              class="mb-4"
              :rules="awardNumberRules"
            />

            <div class="text-h5 mb-2">
              Grant End Date
            </div>
            <div class="mb-3">
              When does this grant/award period end? This will be used to determine the embargo end date.
            </div>
            <v-text-field
              v-model="grantEndDate"
              label="Grant end date"
              type="date"
              required
              variant="outlined"
              density="compact"
              class="mb-4"
              :rules="grantEndDateRules"
            />
          </div>

          <div v-else>
            <div class="text-h5 mb-2">
              Embargo End Date
            </div>
            <div class="mb-3">
              Since this Dandiset is not associated with a research award, the embargo will automatically end 2 years from today.
            </div>
            <v-text-field
              v-model="embargoEndDate"
              label="Embargo end date"
              readonly
              variant="outlined"
              density="compact"
              class="mb-4"
            />
          </div>
        </div>
        <small class="float-right font-weight-bold">All fields above are required</small>

        <v-divider class="mt-10 mb-6" />

        <div class="text-h4">
          Additional metadata
        </div>
        <div>
          The sections below are optional, and you can add or change any of them
          later through the <strong>METADATA</strong> editor on the Dandiset page.
          Filling them in now is the easiest way to make the Dandiset findable,
          citable, and reusable. Contributors are required before a Dandiset can
          be published, and the rest are highly recommended. See the
          <a
            :href="`${dandiDocumentationUrl}/user-guide-sharing/dandiset-metadata/`"
            target="_blank"
            rel="noopener"
          >Dandiset metadata guide</a>
          for details on each section.
        </div>

        <OptionalSection title="Contributors">
          <template #description>
            Everyone who should be credited for this data, in the order they
            should appear in the citation. Use the form "Last, First". ORCID
            identifiers are strongly encouraged so that credit is attributed
            correctly. One contributor must have the Contact Person role and an
            email address; if none does, you will be added as the contact.
          </template>
          <RowList
            v-model="contributors"
            :blank="blankContributor"
            item-label="contributor"
          >
            <template #default="{ row }">
              <v-row dense>
                <v-col
                  cols="12"
                  md="3"
                >
                  <v-text-field
                    v-model="row.name"
                    label="Name (Last, First)"
                    :rules="[requiredUnless(contributorIsEmpty(row), 'Name is required'), personNameRule]"
                    variant="outlined"
                    density="compact"
                  />
                </v-col>
                <v-col
                  cols="12"
                  md="2"
                >
                  <v-text-field
                    v-model="row.orcid"
                    label="ORCID"
                    placeholder="0000-0002-1825-0097"
                    :rules="[orcidRuleNormalized]"
                    variant="outlined"
                    density="compact"
                  />
                </v-col>
                <v-col
                  cols="12"
                  md="3"
                >
                  <v-text-field
                    v-model="row.email"
                    label="Email"
                    :rules="[contactEmailRule(row), emailRule]"
                    variant="outlined"
                    density="compact"
                  />
                </v-col>
                <v-col
                  cols="12"
                  md="4"
                >
                  <v-select
                    v-model="row.roles"
                    :items="PERSON_ROLES"
                    label="Roles"
                    multiple
                    chips
                    closable-chips
                    variant="outlined"
                    density="compact"
                  />
                </v-col>
              </v-row>
            </template>
          </RowList>
        </OptionalSection>

        <OptionalSection title="Funding">
          <template #description>
            The organizations that funded this work, one entry per award number.
            Look up the funder on
            <a
              href="https://ror.org"
              target="_blank"
              rel="noopener"
            >ror.org</a>
            and paste its ROR identifier; many organizations have similar names
            (several countries have an "NIH"), so check that the entry matches.
            <span v-if="embargoed && hasAward">
              The award entered above is added automatically and does not need to be repeated here.
            </span>
          </template>
          <RowList
            v-model="funders"
            :blank="blankFunding"
            item-label="funder"
          >
            <template #default="{ row }">
              <v-row dense>
                <v-col
                  cols="12"
                  md="5"
                >
                  <v-text-field
                    v-model="row.name"
                    label="Funder name"
                    placeholder="National Institute of Neurological Disorders and Stroke"
                    :rules="[requiredUnless(fundingIsEmpty(row), 'Funder name is required')]"
                    variant="outlined"
                    density="compact"
                  />
                </v-col>
                <v-col
                  cols="12"
                  md="4"
                >
                  <v-text-field
                    v-model="row.ror"
                    label="ROR identifier"
                    placeholder="https://ror.org/01s5ya894"
                    :rules="[rorRule]"
                    variant="outlined"
                    density="compact"
                  />
                </v-col>
                <v-col
                  cols="12"
                  md="3"
                >
                  <v-text-field
                    v-model="row.awardNumber"
                    label="Award number"
                    variant="outlined"
                    density="compact"
                  />
                </v-col>
              </v-row>
            </template>
          </RowList>
        </OptionalSection>

        <OptionalSection title="Subject matter">
          <template #description>
            The brain regions, disorders, and other topics this data is about.
            Where possible, include the identifier of a matching ontology term,
            for example a
            <a
              href="https://www.ebi.ac.uk/ols4/ontologies/uberon"
              target="_blank"
              rel="noopener"
            >UBERON</a>
            term for anatomy, so that the Dandiset can be found by searches on
            that term.
          </template>
          <RowList
            v-model="subjects"
            :blank="blankSubject"
            item-label="term"
          >
            <template #default="{ row }">
              <v-row dense>
                <v-col
                  cols="12"
                  md="3"
                >
                  <v-select
                    v-model="row.kind"
                    :items="SUBJECT_KINDS"
                    label="Type"
                    variant="outlined"
                    density="compact"
                  />
                </v-col>
                <v-col
                  cols="12"
                  md="4"
                >
                  <v-text-field
                    v-model="row.name"
                    label="Term"
                    placeholder="primary visual cortex"
                    :rules="[requiredUnless(subjectIsEmpty(row), 'Term is required')]"
                    variant="outlined"
                    density="compact"
                  />
                </v-col>
                <v-col
                  cols="12"
                  md="5"
                >
                  <v-text-field
                    v-model="row.identifier"
                    label="Ontology identifier"
                    placeholder="http://purl.obolibrary.org/obo/UBERON_0002436"
                    variant="outlined"
                    density="compact"
                  />
                </v-col>
              </v-row>
            </template>
          </RowList>
        </OptionalSection>

        <OptionalSection title="Ethics approvals">
          <template #description>
            The animal or human subjects protocols under which the experiments
            were performed, for example an IACUC or IRB protocol number, with a
            link to the approving committee if one exists.
          </template>
          <RowList
            v-model="ethics"
            :blank="blankEthics"
            item-label="approval"
          >
            <template #default="{ row }">
              <v-row dense>
                <v-col
                  cols="12"
                  md="5"
                >
                  <v-text-field
                    v-model="row.identifier"
                    label="Protocol identifier"
                    placeholder="IACUC 2021-0123"
                    :rules="[requiredUnless(ethicsIsEmpty(row), 'Protocol identifier is required')]"
                    variant="outlined"
                    density="compact"
                  />
                </v-col>
                <v-col
                  cols="12"
                  md="7"
                >
                  <v-text-field
                    v-model="row.url"
                    label="Committee URL"
                    :rules="[urlRule]"
                    variant="outlined"
                    density="compact"
                  />
                </v-col>
              </v-row>
            </template>
          </RowList>
        </OptionalSection>

        <OptionalSection title="Related resources">
          <template #description>
            Links that put this data in context: the publication or preprint it
            accompanies, the code used to convert it to NWB, analysis code,
            example notebooks, and related datasets on DANDI or elsewhere. Choose
            the kind of resource and the relation is filled in for you; the
            relation reads as "this Dandiset <em>relation</em> resource".
          </template>
          <RowList
            v-model="resources"
            :blank="blankResource"
            item-label="resource"
          >
            <template #default="{ row }">
              <v-row dense>
                <v-col
                  cols="12"
                  md="4"
                >
                  <v-select
                    v-model="row.kind"
                    :items="RESOURCE_KINDS"
                    label="Kind"
                    variant="outlined"
                    density="compact"
                    @update:model-value="applyResourceKind(row)"
                  />
                </v-col>
                <v-col
                  cols="12"
                  md="5"
                >
                  <v-text-field
                    v-model="row.url"
                    label="URL"
                    placeholder="https://doi.org/10.1000/xyz123"
                    :rules="[requiredUnless(resourceIsEmpty(row), 'URL is required'), urlRule]"
                    variant="outlined"
                    density="compact"
                  />
                </v-col>
                <v-col
                  cols="12"
                  md="3"
                >
                  <v-select
                    v-model="row.relation"
                    :items="RELATION_TYPES"
                    label="Relation"
                    variant="outlined"
                    density="compact"
                  />
                </v-col>
                <v-col cols="12">
                  <v-text-field
                    v-model="row.name"
                    label="Title of the resource"
                    variant="outlined"
                    density="compact"
                  />
                </v-col>
              </v-row>
            </template>
          </RowList>
        </OptionalSection>

        <OptionalSection title="Keywords">
          <template #description>
            Free-text terms that describe the data, such as techniques, cell
            types, or behaviors. Press Enter after each keyword.
          </template>
          <v-combobox
            v-model="keywords"
            label="Keywords"
            multiple
            chips
            closable-chips
            variant="outlined"
            density="compact"
          />
        </OptionalSection>
      </v-form>
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn
        type="submit"
        color="primary"
        :disabled="saveDisabled"
        variant="flat"
        @click="registerDandiset"
      >
        Register Dandiset
        <template #loader>
          <span>Registering...</span>
        </template>
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import type { ComputedRef } from 'vue';
import { dandiRest, loggedIn, user } from '@/rest';
import { useDandisetStore } from '@/stores/dandiset';
import { dandiDocumentationUrl, sandboxDocsUrl } from '@/utils/constants';

import type {
  DandisetContributors,
  DandisetMetadata,
  LicenseType,
  Person,
} from '@/types';

import OptionalSection from './OptionalSection.vue';
import RowList from './RowList.vue';
import {
  PERSON_ROLES,
  RELATION_TYPES,
  RESOURCE_KINDS,
  SUBJECT_KINDS,
  blankContributor,
  blankEthics,
  blankFunding,
  blankResource,
  blankSubject,
  contributorIsEmpty,
  contributorIsValid,
  contributorToPerson,
  ethicsIsEmpty,
  ethicsIsValid,
  ethicsToApproval,
  fundingIsEmpty,
  fundingIsValid,
  fundingToOrganization,
  resourceIsEmpty,
  resourceIsValid,
  resourceToRelated,
  subjectIsEmpty,
  subjectIsValid,
  subjectToAbout,
} from './metadataRows';
import type {
  ContributorRow,
  EthicsRow,
  FundingRow,
  ResourceRow,
  SubjectRow,
} from './metadataRows';
import type { Rule } from './validation';
import {
  emailRule,
  normalizeOrcid,
  orcidRule,
  personNameRule,
  rorRule,
  toLastFirst,
  urlRule,
} from './validation';

const router = useRouter();
const store = useDandisetStore();

const name = ref('');
const description = ref('');
const license = ref<LicenseType>();
const embargoed = ref(false);
const hasAward = ref(true);
const fundingSource = ref('');
const awardNumber = ref('');
const grantEndDate = ref('');

// Optional metadata. The creating user is offered as the first contributor
// and contact person, mirroring what the server would otherwise fill in.
function currentUserRow(): ContributorRow {
  return {
    name: toLastFirst(user.value?.name ?? ''),
    orcid: '',
    email: user.value?.email ?? '',
    roles: ['dcite:ContactPerson', 'dcite:Author'],
  };
}
const contributors = ref<ContributorRow[]>(user.value ? [currentUserRow()] : []);
const funders = ref<FundingRow[]>([]);
const subjects = ref<SubjectRow[]>([]);
const ethics = ref<EthicsRow[]>([]);
const resources = ref<ResourceRow[]>([]);
const keywords = ref<string[]>([]);

const orcidRuleNormalized: Rule = (v) => orcidRule(v ? normalizeOrcid(v) : v);

// A field is required once anything in its row has been filled in; a wholly
// blank row is simply ignored at submit time.
function requiredUnless(rowIsEmpty: boolean, message: string): Rule {
  return (v) => rowIsEmpty || !!v?.trim() || message;
}

function contactEmailRule(row: ContributorRow): Rule {
  return (v) => !row.roles.includes('dcite:ContactPerson')
    || !!v?.trim()
    || 'The contact person needs an email address';
}

function applyResourceKind(row: ResourceRow) {
  const kind = RESOURCE_KINDS.find((k) => k.value === row.kind);
  if (kind) row.relation = kind.relation;
}

const optionalMetadataValid = computed(
  () => contributors.value.every(contributorIsValid)
      && funders.value.every(fundingIsValid)
      && subjects.value.every(subjectIsValid)
      && ethics.value.every(ethicsIsValid)
      && resources.value.every(resourceIsValid),
);

// Calculate embargo end date as 2 years from today
const embargoEndDate = computed(() => {
  const today = new Date();
  const twoYearsFromNow = new Date(today.getFullYear() + 2, today.getMonth(), today.getDate());
  return twoYearsFromNow.toISOString().split('T')[0];
});

// Helper function to validate grant end date bounds
const isGrantEndDateValid = computed(() => {
  if (!grantEndDate.value) return false; // Required field

  const selectedDate = new Date(grantEndDate.value);
  const today = new Date();
  const fiveYearsFromNow = new Date(today.getFullYear() + 5, today.getMonth(), today.getDate());

  // Check if date is in the past or more than 5 years in the future
  return selectedDate >= today && selectedDate <= fiveYearsFromNow;
});

const saveDisabled = computed(
  () => !name.value
      || !description.value
      || !optionalMetadataValid.value
      || (!embargoed.value && !license.value)
      || (embargoed.value && hasAward.value
        && (!fundingSource.value || !awardNumber.value || !grantEndDate.value || !isGrantEndDateValid.value))
      || (embargoed.value && !hasAward.value && !embargoEndDate.value),
);

const fundingSourceRules = computed(
  () => [(v: string) => !!v || 'Funding source is required'],
);

// The server rejects a funding source without an award number.
const awardNumberRules = computed(
  () => [(v: string) => !!v || 'Award number (or project name) is required'],
);

const grantEndDateRules = computed(() => [
  (v: string) => !!v || 'Grant end date is required',
  (v: string) => {
    if (!v) return true; // Skip validation if empty (handled by required rule)

    const selectedDate = new Date(v);
    const today = new Date();
    const fiveYearsFromNow = new Date(today.getFullYear() + 5, today.getMonth(), today.getDate());

    // Check if date is in the past
    if (selectedDate < today) {
      return 'Grant end date cannot be in the past';
    }

    // Check if date is more than 5 years in the future
    if (selectedDate > fiveYearsFromNow) {
      return 'DANDI only supports 5 years of embargo';
    }

    return true;
  },
]);

const nameMaxLength: ComputedRef<number> = computed(() => store.schema.properties.name.maxLength);
const descriptionMaxLength: ComputedRef<number> = computed(
  () => store.schema.properties.description.maxLength,
);
const dandiLicenses: ComputedRef<LicenseType[]> = computed(
  () => store.schema.$defs.LicenseType.enum,
);

// Try to guess if the Dandiset is a test Dandiset based on the name, and show a warning if so.
const showTestWarning = computed(() => name.value.toLowerCase().includes('test'));

// Example text shown as placeholders and in the short-title hint, to illustrate
// the level of detail that makes a Dandiset findable and reusable.
const titlePlaceholder = 'Neuropixels recordings from mouse visual cortex during a visual discrimination task';
const descriptionPlaceholder = 'Extracellular recordings from primary visual cortex (V1) and lateral '
  + 'geniculate nucleus (LGN) of 12 adult C57BL/6J mice performing a two-alternative forced-choice '
  + 'orientation discrimination task. Each session includes spike-sorted units, LFP, running speed, '
  + 'pupil diameter, and trial-by-trial stimulus and choice information. One NWB file per session, '
  + 'organized by subject.';

// Soft, non-blocking hints that the title or description is probably too short
// to be useful. Thresholds are loose so that genuinely brief but adequate text
// does not trigger them.
const MIN_TITLE_WORDS = 5;
const MIN_DESCRIPTION_WORDS = 50;
function wordCount(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}
const showShortTitleHint = computed(
  () => name.value.trim().length > 0 && wordCount(name.value) < MIN_TITLE_WORDS,
);
const showShortDescriptionHint = computed(
  () => description.value.trim().length > 0 && wordCount(description.value) < MIN_DESCRIPTION_WORDS,
);

if (!loggedIn()) {
  router.push({ name: 'home' });
}

// Assemble the optional metadata into schema objects, leaving out any section
// the user did not fill in so that server-side defaults still apply.
function optionalMetadata(): Partial<DandisetMetadata> {
  const metadata: Partial<DandisetMetadata> = {};

  const persons = contributors.value
    .filter((row) => !contributorIsEmpty(row))
    .map(contributorToPerson);
  const organizations = funders.value
    .filter((row) => !fundingIsEmpty(row))
    .map(fundingToOrganization);
  if (persons.length || organizations.length) {
    // The server only adds the creating user as contact person when no
    // contributors are supplied, so make sure a contact exists here.
    const hasContact = persons.some((p) => p.roleName?.includes('dcite:ContactPerson'));
    if (!hasContact && user.value) {
      const contact: Person = contributorToPerson({
        ...currentUserRow(),
        roles: ['dcite:ContactPerson'],
      });
      persons.unshift(contact);
    }
    metadata.contributor = [...persons, ...organizations] as DandisetContributors;
  }

  const about = subjects.value.filter((row) => !subjectIsEmpty(row)).map(subjectToAbout);
  if (about.length) metadata.about = about;

  const approvals = ethics.value.filter((row) => !ethicsIsEmpty(row)).map(ethicsToApproval);
  if (approvals.length) metadata.ethicsApproval = approvals;

  const related = resources.value.filter((row) => !resourceIsEmpty(row)).map(resourceToRelated);
  if (related.length) metadata.relatedResource = related;

  const terms = keywords.value.map((k) => k.trim()).filter(Boolean);
  if (terms.length) metadata.keywords = terms;

  return metadata;
}

async function registerDandiset() {
  const metadata: Partial<DandisetMetadata> = {
    name: name.value,
    description: description.value,
    ...optionalMetadata(),
  };

  if (license.value) {
    metadata.license = [license.value];
  }

  if (embargoed.value) {
    // When a funding source is given, the server appends it to the contributor
    // list exactly as submitted, so the contact person has to be present here
    // rather than left for the server default.
    if (!metadata.contributor && user.value) {
      metadata.contributor = [
        contributorToPerson({ ...currentUserRow(), roles: ['dcite:ContactPerson'] }),
      ];
    }

    const embargoData = {
      hasAward: hasAward.value,
      fundingSource: hasAward.value ? fundingSource.value : undefined,
      awardNumber: hasAward.value ? awardNumber.value : undefined,
      embargoEndDate: hasAward.value ? grantEndDate.value : embargoEndDate.value,
    };

    const { data } = await dandiRest.createEmbargoedDandiset(name.value, metadata, embargoData);
    const { identifier } = data;
    router.push({ name: 'dandisetLanding', params: { identifier } });
  } else {
    const { data } = await dandiRest.createDandiset(name.value, metadata);
    const { identifier } = data;
    router.push({ name: 'dandisetLanding', params: { identifier } });
  }
}

</script>
