import { useState } from 'react';

/** Selection is scoped to the visible page and filter, never hidden records. */
export function usePageSelection(scope: string, ids: string[]) {
  const [state, setState] = useState<{ scope: string; ids: string[] }>({
    scope,
    ids: [],
  });
  const selected =
    state.scope === scope ? state.ids.filter((id) => ids.includes(id)) : [];
  function toggle(id: string, checked: boolean) {
    setState((previous) => {
      const current =
        previous.scope === scope
          ? previous.ids.filter((value) => ids.includes(value))
          : [];
      return {
        scope,
        ids: checked
          ? [...new Set([...current, id])]
          : current.filter((value) => value !== id),
      };
    });
  }
  return {
    selected,
    toggle,
    all: ids.length > 0 && selected.length === ids.length,
    some: selected.length > 0,
    toggleAll: (checked: boolean) =>
      setState({ scope, ids: checked ? ids : [] }),
    remove: (done: string[]) =>
      setState({ scope, ids: selected.filter((id) => !done.includes(id)) }),
  };
}
