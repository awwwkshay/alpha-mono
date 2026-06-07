import { useEffect, useState } from "react";

import { STUDIO_SYNC_EVENT } from "@/lib/api";

type LoadState<T> =
  | { status: "loading"; data: null; error: null }
  | { status: "ready"; data: T; error: null }
  | { status: "error"; data: null; error: string };

export function useApi<T>(load: () => Promise<T>): LoadState<T> {
  const [state, setState] = useState<LoadState<T>>({
    status: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    let active = true;

    function reload() {
      void load()
        .then((data) => {
          if (active) {
            setState({ status: "ready", data, error: null });
          }
        })
        .catch((error: unknown) => {
          if (active) {
            const message = error instanceof Error ? error.message : "Request failed";
            setState({ status: "error", data: null, error: message });
          }
        });
    }

    reload();
    window.addEventListener(STUDIO_SYNC_EVENT, reload);

    return () => {
      active = false;
      window.removeEventListener(STUDIO_SYNC_EVENT, reload);
    };
  }, [load]);

  return state;
}
