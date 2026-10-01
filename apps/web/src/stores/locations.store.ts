import { computed } from 'vue';
import { defineStore } from 'pinia';
import { useObservationsStore } from './observations.store';

export interface LocationNode {
  id: string;
  label: string;
  kind: 'site' | 'building' | 'storey' | 'space' | 'zone' | 'sensor';
  children: LocationNode[];
}

export const useLocationsStore = defineStore('locations', () => {
  const observations = useObservationsStore();

  const hierarchy = computed<LocationNode[]>(() => {
    const roots: LocationNode[] = [];
    for (const item of observations.history) {
      const path: Array<{ id: string | null; label: string | null; kind: LocationNode['kind'] }> = [
        { id: item.siteId, label: item.siteLabel, kind: 'site' as const },
        { id: item.buildingId, label: item.buildingLabel, kind: 'building' as const },
        { id: item.storeyId, label: item.storeyLabel, kind: 'storey' as const },
        { id: item.spaceId, label: item.spaceLabel, kind: 'space' as const },
        { id: item.zoneId, label: item.zoneLabel, kind: 'zone' as const },
        { id: item.nodeId, label: item.nodeId, kind: 'sensor' as const },
      ];
      let level = roots;
      for (const entry of path) {
        if (!entry.id) continue;
        const id = entry.id;
        let node = level.find((candidate) => candidate.id === id && candidate.kind === entry.kind);
        if (!node) {
          node = { id, label: entry.label ?? id, kind: entry.kind, children: [] };
          level.push(node);
        }
        level = node.children;
      }
    }
    return roots;
  });

  return { hierarchy };
});
