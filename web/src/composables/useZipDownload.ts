import { ref } from 'vue';
import { downloadZip } from 'client-zip';

export interface ZipEntry {
  /** Path of the file inside the zip. */
  name: string;
  /** URL to fetch the file's bytes from. */
  url: string;
  /** Size in bytes, used for progress tracking. */
  size: number;
  lastModified?: Date;
}

// Wrap a byte stream so we can count bytes as they flow through to the zipper,
// giving smooth progress even when the download is a few large files.
function trackStream(
  stream: ReadableStream<Uint8Array>,
  onBytes: (n: number) => void,
): ReadableStream<Uint8Array> {
  const reader = stream.getReader();
  return new ReadableStream<Uint8Array>({
    async pull(controller) {
      const { done, value } = await reader.read();
      if (done) {
        controller.close();
        return;
      }
      onBytes(value.byteLength);
      controller.enqueue(value);
    },
    cancel(reason) {
      reader.cancel(reason);
    },
  });
}

/**
 * Generic in-browser zip download: fetch a list of URLs sequentially, zip them
 * client-side with client-zip, and save the result through the browser's normal
 * download mechanism.
 *
 * The URLs are fetched with a plain (unauthenticated) `fetch`, so they must be
 * publicly readable and CORS-accessible. The archive is buffered in memory
 * before saving, so callers should gate usage on a reasonable total size.
 */
export function useZipDownload() {
  const inProgress = ref(false);
  const progress = ref(0); // 0–100
  const canceled = ref(false);

  let abortController: AbortController | null = null;

  function cancel() {
    abortController?.abort();
  }

  /**
   * Fetch entries and save them as `zipName`. `getEntries` receives an
   * AbortSignal so that entry listing is interrupted by `cancel()` along with
   * any in-flight fetches. Throws on failure; after a `cancel()` the rejection
   * is the abort reason and `canceled` is set.
   */
  async function download(
    zipName: string,
    getEntries: (signal: AbortSignal) => Promise<ZipEntry[]>,
  ): Promise<void> {
    if (inProgress.value) {
      return;
    }
    inProgress.value = true;
    progress.value = 0;
    canceled.value = false;
    abortController = new AbortController();
    const { signal } = abortController;

    try {
      const entries = await getEntries(signal);
      const totalBytes = entries.reduce((sum, entry) => sum + entry.size, 0);
      let downloadedBytes = 0;

      // Lazily fetch each entry so only one file is in flight at a time.
      async function* zipEntries() {
        for (const entry of entries) {
          const response = await fetch(entry.url, { signal });
          if (!response.ok) {
            throw new Error(`Failed to download "${entry.name}" (HTTP ${response.status})`);
          }
          const body = response.body
            ? trackStream(response.body, (n) => {
              downloadedBytes += n;
              progress.value = totalBytes ? (downloadedBytes / totalBytes) * 100 : 0;
            })
            : response;
          yield {
            name: entry.name,
            input: body,
            size: entry.size,
            lastModified: entry.lastModified,
          };
        }
      }

      const blob = await downloadZip(zipEntries()).blob();

      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = objectUrl;
      link.download = zipName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(objectUrl);
    } catch (err) {
      canceled.value = signal.aborted;
      throw err;
    } finally {
      inProgress.value = false;
      abortController = null;
    }
  }

  return {
    inProgress, progress, canceled, cancel, download,
  };
}
