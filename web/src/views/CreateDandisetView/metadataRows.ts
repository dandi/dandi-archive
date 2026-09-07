// Row models for the optional metadata sections of the Dandiset creation form,
// with conversion to the dandischema objects sent to the API. Rows are kept
// flat and string-valued so they bind directly to text fields; blank rows are
// dropped at submit time.

import type {
  Anatomy,
  Disorder,
  EthicsApproval,
  GenericType,
  Organization,
  Person,
  ResourceRelation as RelationType,
  Resource,
  ResourceType,
  RoleType,
} from '@/types';
import {
  allValid,
  emailRule,
  normalizeOrcid,
  orcidRule,
  personNameRule,
  rorRule,
  urlRule,
} from './validation';

// Contributors --------------------------------------------------------------

export interface ContributorRow {
  name: string;
  orcid: string;
  email: string;
  roles: RoleType[];
}

// Roles a person can reasonably be given at creation time. Organization-only
// roles (Funder, Sponsor, Affiliation) and roles the editor handles better are
// left out.
export const PERSON_ROLES: { title: string; value: RoleType }[] = [
  { title: 'Author', value: 'dcite:Author' },
  { title: 'Contact Person', value: 'dcite:ContactPerson' },
  { title: 'Conceptualization', value: 'dcite:Conceptualization' },
  { title: 'Data Collector', value: 'dcite:DataCollector' },
  { title: 'Data Curator', value: 'dcite:DataCurator' },
  { title: 'Data Manager', value: 'dcite:DataManager' },
  { title: 'Formal Analysis', value: 'dcite:FormalAnalysis' },
  { title: 'Funding Acquisition', value: 'dcite:FundingAcquisition' },
  { title: 'Investigation', value: 'dcite:Investigation' },
  { title: 'Methodology', value: 'dcite:Methodology' },
  { title: 'Project Leader', value: 'dcite:ProjectLeader' },
  { title: 'Project Member', value: 'dcite:ProjectMember' },
  { title: 'Researcher', value: 'dcite:Researcher' },
  { title: 'Software', value: 'dcite:Software' },
  { title: 'Supervision', value: 'dcite:Supervision' },
  { title: 'Validation', value: 'dcite:Validation' },
  { title: 'Visualization', value: 'dcite:Visualization' },
  { title: 'Other', value: 'dcite:Other' },
];

export function blankContributor(): ContributorRow {
  return {
    name: '', orcid: '', email: '', roles: ['dcite:Author'],
  };
}

export function contributorIsEmpty(row: ContributorRow): boolean {
  return !row.name.trim() && !row.orcid.trim() && !row.email.trim();
}

export function contributorIsValid(row: ContributorRow): boolean {
  if (contributorIsEmpty(row)) return true;
  return row.name.trim().length > 0
    && allValid([personNameRule], row.name)
    && allValid([orcidRule], normalizeOrcid(row.orcid))
    && allValid([emailRule], row.email)
    && (!row.roles.includes('dcite:ContactPerson') || row.email.trim().length > 0);
}

export function contributorToPerson(row: ContributorRow): Person {
  const person: Person = {
    schemaKey: 'Person',
    name: row.name.trim(),
    roleName: row.roles,
    includeInCitation: true,
    affiliation: [],
  };
  const orcid = normalizeOrcid(row.orcid);
  if (orcid) person.identifier = orcid;
  if (row.email.trim()) person.email = row.email.trim();
  return person;
}

// Funding -------------------------------------------------------------------

export interface FundingRow {
  name: string;
  ror: string;
  awardNumber: string;
}

export function blankFunding(): FundingRow {
  return { name: '', ror: '', awardNumber: '' };
}

export function fundingIsEmpty(row: FundingRow): boolean {
  return !row.name.trim() && !row.ror.trim() && !row.awardNumber.trim();
}

export function fundingIsValid(row: FundingRow): boolean {
  if (fundingIsEmpty(row)) return true;
  return row.name.trim().length > 0 && allValid([rorRule], row.ror);
}

export function fundingToOrganization(row: FundingRow): Organization {
  const org: Organization = {
    schemaKey: 'Organization',
    name: row.name.trim(),
    roleName: ['dcite:Funder'],
    includeInCitation: false,
  };
  if (row.ror.trim()) org.identifier = row.ror.trim();
  if (row.awardNumber.trim()) org.awardNumber = row.awardNumber.trim();
  return org;
}

// Subject matter ------------------------------------------------------------

export type SubjectKind = 'Anatomy' | 'Disorder' | 'GenericType';

export interface SubjectRow {
  kind: SubjectKind;
  name: string;
  identifier: string;
}

export const SUBJECT_KINDS: { title: string; value: SubjectKind }[] = [
  { title: 'Anatomy', value: 'Anatomy' },
  { title: 'Disorder', value: 'Disorder' },
  { title: 'Other', value: 'GenericType' },
];

export function blankSubject(): SubjectRow {
  return { kind: 'Anatomy', name: '', identifier: '' };
}

export function subjectIsEmpty(row: SubjectRow): boolean {
  return !row.name.trim() && !row.identifier.trim();
}

export function subjectIsValid(row: SubjectRow): boolean {
  if (subjectIsEmpty(row)) return true;
  return row.name.trim().length > 0;
}

export function subjectToAbout(row: SubjectRow): Anatomy | Disorder | GenericType {
  const term = { schemaKey: row.kind, name: row.name.trim() } as Anatomy | Disorder | GenericType;
  if (row.identifier.trim()) term.identifier = row.identifier.trim();
  return term;
}

// Ethics approvals ----------------------------------------------------------

export interface EthicsRow {
  identifier: string;
  url: string;
}

export function blankEthics(): EthicsRow {
  return { identifier: '', url: '' };
}

export function ethicsIsEmpty(row: EthicsRow): boolean {
  return !row.identifier.trim() && !row.url.trim();
}

export function ethicsIsValid(row: EthicsRow): boolean {
  if (ethicsIsEmpty(row)) return true;
  return row.identifier.trim().length > 0 && allValid([urlRule], row.url);
}

export function ethicsToApproval(row: EthicsRow): EthicsApproval {
  const approval: EthicsApproval = {
    schemaKey: 'EthicsApproval',
    identifier: row.identifier.trim(),
  };
  if (row.url.trim()) {
    approval.contactPoint = { schemaKey: 'ContactPoint', url: row.url.trim() };
  }
  return approval;
}

// Related resources ---------------------------------------------------------

export type ResourceKind =
  | 'publication'
  | 'preprint'
  | 'dataPaper'
  | 'analysisPaper'
  | 'conversionCode'
  | 'analysisCode'
  | 'notebook'
  | 'dataset'
  | 'other';

export interface ResourceRow {
  kind: ResourceKind;
  url: string;
  name: string;
  relation: RelationType;
}

// Friendly resource kinds, mapped to the relation and resource type that the
// metadata guide recommends or that existing Dandisets most commonly use.
// The relation reads as "Dandiset <relation> resource".
export const RESOURCE_KINDS: {
  title: string;
  value: ResourceKind;
  relation: RelationType;
  resourceType?: ResourceType;
}[] = [
  {
    title: 'Journal article describing this data', value: 'publication', relation: 'dcite:IsDescribedBy', resourceType: 'dcite:JournalArticle',
  },
  {
    title: 'Preprint describing this data', value: 'preprint', relation: 'dcite:IsDescribedBy', resourceType: 'dcite:Preprint',
  },
  {
    title: 'Data descriptor paper', value: 'dataPaper', relation: 'dcite:IsDocumentedBy', resourceType: 'dcite:DataPaper',
  },
  {
    title: 'Later publication that analyzes this data', value: 'analysisPaper', relation: 'dcite:IsCitedBy', resourceType: 'dcite:JournalArticle',
  },
  {
    title: 'Code used to convert the data to NWB', value: 'conversionCode', relation: 'dcite:IsCompiledBy', resourceType: 'dcite:Software',
  },
  {
    title: 'Analysis code or library for this data', value: 'analysisCode', relation: 'dcite:IsSupplementedBy', resourceType: 'dcite:Software',
  },
  {
    title: 'Example notebook', value: 'notebook', relation: 'dcite:IsSupplementedBy', resourceType: 'dcite:ComputationalNotebook',
  },
  {
    title: 'Related dataset', value: 'dataset', relation: 'dcite:IsSupplementedBy', resourceType: 'dcite:Dataset',
  },
  {
    title: 'Other', value: 'other', relation: 'dcite:IsReferencedBy',
  },
];

export const RELATION_TYPES: { title: string; value: RelationType }[] = [
  'dcite:IsCitedBy', 'dcite:Cites', 'dcite:IsSupplementTo', 'dcite:IsSupplementedBy',
  'dcite:IsContinuedBy', 'dcite:Continues', 'dcite:Describes', 'dcite:IsDescribedBy',
  'dcite:HasMetadata', 'dcite:IsMetadataFor', 'dcite:HasVersion', 'dcite:IsVersionOf',
  'dcite:IsNewVersionOf', 'dcite:IsPreviousVersionOf', 'dcite:IsPartOf', 'dcite:HasPart',
  'dcite:IsReferencedBy', 'dcite:References', 'dcite:IsDocumentedBy', 'dcite:Documents',
  'dcite:IsCompiledBy', 'dcite:Compiles', 'dcite:IsVariantFormOf', 'dcite:IsOriginalFormOf',
  'dcite:IsIdenticalTo', 'dcite:IsReviewedBy', 'dcite:Reviews', 'dcite:IsDerivedFrom',
  'dcite:IsSourceOf', 'dcite:IsRequiredBy', 'dcite:Requires', 'dcite:Obsoletes',
  'dcite:IsObsoletedBy', 'dcite:IsPublishedIn',
].map((value) => ({ title: value.replace('dcite:', ''), value: value as RelationType }));

export function blankResource(): ResourceRow {
  return {
    kind: 'publication', url: '', name: '', relation: 'dcite:IsDescribedBy',
  };
}

export function resourceIsEmpty(row: ResourceRow): boolean {
  return !row.url.trim() && !row.name.trim();
}

export function resourceIsValid(row: ResourceRow): boolean {
  if (resourceIsEmpty(row)) return true;
  return row.url.trim().length > 0 && allValid([urlRule], row.url);
}

export function resourceToRelated(row: ResourceRow): Resource {
  const kind = RESOURCE_KINDS.find((k) => k.value === row.kind);
  const resource: Resource = {
    schemaKey: 'Resource',
    url: row.url.trim(),
    relation: row.relation,
  };
  if (row.name.trim()) resource.name = row.name.trim();
  if (kind?.resourceType) resource.resourceType = kind.resourceType;
  return resource;
}
