import type { Ref } from 'vue';
import { computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

/*
 * The URL hash records what is open on a Dandiset landing page, so a view can be
 * linked to and comes back on reload:
 *
 *   #how-to-cite                   the How to Cite tab (any tab: its label in lowercase,
 *                                  with dashes for spaces, e.g. #notebooks)
 *   #how-to-cite=mla               ... with a citation style chosen
 *   #metadata                      the metadata editor
 *   #release-notes=0.230629.1955   a version's release notes
 *
 * The Overview tab has no anchor. Changes replace the current history entry, so Back
 * still leaves the page.
 */

export interface LandingAnchor {
  key: string;
  value: string;
}

export function parseAnchor(hash: string): LandingAnchor {
  let raw = hash.replace(/^#/, '');
  try {
    raw = decodeURIComponent(raw);
  } catch {
    // Keep a malformed hash as it is; it just won't match anything.
  }
  const eq = raw.indexOf('=');
  return eq < 0 ? { key: raw, value: '' } : { key: raw.slice(0, eq), value: raw.slice(eq + 1) };
}

export function formatAnchor(key: string | null, value?: string): string {
  if (!key) {
    return '';
  }
  return value ? `#${key}=${encodeURIComponent(value)}` : `#${key}`;
}

/** The anchor for a tab, from its label: "How to Cite" -> "how-to-cite". */
export function tabAnchor(label: string): string {
  return label.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}

export function useLandingAnchor() {
  const route = useRoute();
  const router = useRouter();

  const anchor = computed(() => parseAnchor(route.hash));

  function setHash(hash: string) {
    if (hash === route.hash) {
      return;
    }
    router.replace({ path: route.path, query: route.query, hash });
  }

  function setAnchor(key: string | null, value?: string) {
    setHash(formatAnchor(key, value));
  }

  /**
   * Keep a dialog and the URL in step: the anchor `key` opens the dialog (when
   * `accept` agrees to the anchor's value), opening the dialog sets the anchor, and
   * closing it puts back the anchor from before it opened (e.g. the current tab).
   * `ready` names data `accept` needs, so the anchor is checked again once it loads.
   */
  function syncDialog(
    open: Ref<boolean>,
    key: string,
    { value, accept, ready }: {
      value?: () => string | undefined;
      accept?: (value: string) => boolean;
      ready?: () => unknown;
    } = {},
  ) {
    let hashBefore = '';
    watch([anchor, () => ready?.()], ([current]) => {
      if (current.key === key && !open.value && (!accept || accept(current.value))) {
        open.value = true;
      }
    }, { immediate: true });
    watch(open, (isOpen) => {
      if (isOpen) {
        if (anchor.value.key !== key) {
          hashBefore = route.hash;
        }
        setAnchor(key, value?.());
      } else if (anchor.value.key === key) {
        setHash(hashBefore);
        hashBefore = '';
      }
    });
  }

  return {
    anchor, setAnchor, syncDialog,
  };
}
