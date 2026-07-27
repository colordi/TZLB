const TIANDITU_IMAGERY_ANNOTATION_URL =
  "https://t0.tianditu.gov.cn/cia_w/wmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&LAYER=cia&STYLE=default&FORMAT=tiles&TILEMATRIXSET=w&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=4267820f43926eaf808d61dc07269beb";

export const BASEMAP_CONFIG = {
  standard: {
    url: "https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
    options: {
      maxZoom: 19,
      attribution:
        "&copy; OpenStreetMap contributors, Tiles style by Humanitarian OpenStreetMap Team hosted by OpenStreetMap France",
    },
  },
  satellite: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    options: {
      maxZoom: 19,
      attribution: "Source: Esri, Vantor, Earthstar Geographics, and the GIS User Community",
    },
    annotation: {
      url: TIANDITU_IMAGERY_ANNOTATION_URL,
      options: {
        maxZoom: 19,
        maxNativeZoom: 18,
        attribution: "&copy; 天地图",
      },
    },
  },
};

export function getBasemapConfig(mode = "standard") {
  return BASEMAP_CONFIG[mode] ?? BASEMAP_CONFIG.standard;
}
