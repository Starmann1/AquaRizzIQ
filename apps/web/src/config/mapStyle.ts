const tileUrl = import.meta.env.VITE_MAP_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const tileAttribution = import.meta.env.VITE_MAP_ATTRIBUTION || '© OpenStreetMap contributors';

/**
 * The provider can be changed at build time. Keep its required attribution
 * visible through MapLibre's native attribution control.
 */
export const streetMapStyle = {
  version: 8 as const,
  sources: {
    base: {
      type: 'raster' as const,
      tiles: [tileUrl],
      tileSize: 256,
      attribution: tileAttribution,
    },
  },
  layers: [{ id: 'base-map', type: 'raster' as const, source: 'base' }],
};
