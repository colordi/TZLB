/** Remove a Leaflet layer held in a Vue ref and null the ref. */
export function clearLayer(layerRef) {
  if (layerRef.value) {
    layerRef.value.remove();
    layerRef.value = null;
  }
}
