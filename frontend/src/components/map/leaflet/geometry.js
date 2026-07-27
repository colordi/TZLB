export function isValidLngLatPair(value) {
  return (
    Array.isArray(value) &&
    value.length >= 2 &&
    Number.isFinite(Number(value[0])) &&
    Number.isFinite(Number(value[1]))
  );
}

export function collectFeatureCoordinatePairs(coordinates, pairs = []) {
  if (isValidLngLatPair(coordinates)) {
    pairs.push([Number(coordinates[0]), Number(coordinates[1])]);
    return pairs;
  }

  if (Array.isArray(coordinates)) {
    coordinates.forEach((item) => collectFeatureCoordinatePairs(item, pairs));
  }

  return pairs;
}

/** @returns {[number, number]|null} Leaflet-style [lat, lng] */
export function extractFeatureLabelLatLng(feature) {
  if (!feature?.geometry) {
    return null;
  }

  const coordinates = feature.geometry.coordinates;
  if (feature.geometry.type === "Point") {
    if (!isValidLngLatPair(coordinates)) {
      return null;
    }

    return [Number(coordinates[1]), Number(coordinates[0])];
  }

  const pairs = collectFeatureCoordinatePairs(coordinates);
  if (!pairs.length) {
    return null;
  }

  const bounds = pairs.reduce(
    (result, [lng, lat]) => ({
      minLng: Math.min(result.minLng, lng),
      maxLng: Math.max(result.maxLng, lng),
      minLat: Math.min(result.minLat, lat),
      maxLat: Math.max(result.maxLat, lat),
    }),
    {
      minLng: Infinity,
      maxLng: -Infinity,
      minLat: Infinity,
      maxLat: -Infinity,
    },
  );

  if (!Number.isFinite(bounds.minLng) || !Number.isFinite(bounds.minLat)) {
    return null;
  }

  return [(bounds.minLat + bounds.maxLat) / 2, (bounds.minLng + bounds.maxLng) / 2];
}

export function isPointFeature(feature) {
  return feature?.geometry?.type === "Point" && isValidLngLatPair(feature.geometry.coordinates);
}

/** @returns {[number, number]|null} Leaflet-style [lat, lng] */
export function getPointFeatureLatLng(feature) {
  if (!isPointFeature(feature)) {
    return null;
  }

  const [lng, lat] = feature.geometry.coordinates;
  return [Number(lat), Number(lng)];
}
