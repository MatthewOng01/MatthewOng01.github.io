"use strict";

const status = document.querySelector("#status");
const search = document.querySelector("#search");
const handle = document.querySelector("#handle");
const parcel = document.querySelector("#parcel");
const byHandle = new Map();
const bins = [
  [-20, "#ad3c35", "Below −20%"],
  [-5, "#e38d6f", "−20% to below −5%"],
  [5, "#e4d9ad", "−5% to below 5%"],
  [20, "#68b9a9", "5% to below 20%"],
  [Infinity, "#11776d", "20% or more"],
];
const missing = "#899398";
const dollars = new Intl.NumberFormat("en-US", {
  style: "currency", currency: "USD", maximumFractionDigits: 0,
});
let selected;
const sidebar = document.querySelector("#sidebar");
const desktopToggle = document.querySelector("#sidebar-toggle");
const mobileToggle = document.querySelector("#mobile-toggle");
const overlay = document.querySelector("#sheet-overlay");
const mobile = matchMedia("(max-width: 767px)");
let desktopOpen = true;
let mobileOpen = false;

function updatePanel() {
  const open = mobile.matches ? mobileOpen : desktopOpen;
  sidebar.classList.toggle("sidebar-hidden", !open);
  sidebar.inert = !open;
  map.getContainer().classList.toggle("sidebar-hidden", !open);
  desktopToggle.classList.toggle("sidebar-hidden", !open);
  desktopToggle.textContent = open ? "◀" : "▶";
  mobileToggle.classList.toggle("sheet-open", mobile.matches && open);
  mobileToggle.textContent = open ? "Close parcel explorer" : "Parcel explorer";
  overlay.classList.toggle("active", mobile.matches && open);
  for (const button of [desktopToggle, mobileToggle]) {
    button.setAttribute("aria-expanded", String(open));
  }
  map.invalidateSize({ pan: false });
}

function style({ properties: { change } }) {
  const color = change == null ? missing : bins.find(([limit]) => change < limit)[1];
  return { color, weight: 0.7, fillColor: color, fillOpacity: 0.76 };
}

function select(layer, zoom) {
  if (selected) selected.setStyle(style(selected.feature));
  selected = layer;
  layer.bringToFront().setStyle({ color: "#0b2024", weight: 3, fillOpacity: 0.9 });
  if (zoom) map.fitBounds(layer.getBounds(), { maxZoom: 18, padding: [35, 35] });
  const p = layer.feature.properties;
  if (mobile.matches && !zoom) {
    mobileOpen = true;
    sidebar.scrollTop = 0;
    updatePanel();
  }
  handle.value = p.HANDLE;
  status.textContent = "Parcel selected.";
  const value = (price, count, label) => price == null ? "Unavailable" :
    `${dollars.format(price)} · ${count} ${label}${count === 1 ? "" : "s"}`;
  const fields = [
    ["HANDLE", p.HANDLE],
    ["Distance to stadium", `${p.miles.toFixed(3)} mi`],
    ["Average assessment · 2010–2015", value(p.assessmentPre, p.yearsPre, "year")],
    ["Average assessment · 2016–2019", value(p.assessmentPost, p.yearsPost, "year")],
    ["Assessment change", p.change == null ? "Unavailable" :
      `${p.change > 0 ? "+" : ""}${p.change.toFixed(1)}%`],
    ["Median sale price · 2010–2015", value(p.salePre, p.salesPre, "sale")],
    ["Median sale price · 2016–2019", value(p.salePost, p.salesPost, "sale")],
  ];
  const list = document.createElement("dl");
  for (const [label, result] of fields) {
    const term = document.createElement("dt");
    const detail = document.createElement("dd");
    const row = document.createElement("div");
    row.className = "popup-row";
    term.className = "popup-key";
    detail.className = "popup-val";
    term.textContent = label;
    detail.textContent = result;
    row.append(term, detail);
    list.append(row);
  }
  parcel.replaceChildren(list);
}

for (const [, color, label] of [...bins, [null, missing, "Unavailable"]]) {
  const item = document.createElement("li");
  const swatch = document.createElement("span");
  swatch.className = "swatch";
  swatch.style.backgroundColor = color;
  item.append(swatch, label);
  document.querySelector("#legend").append(item);
}

const map = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png?key=cb1_2vcy_1_025c4574c20da4ef2887e72e', {
attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors © <a href="https://carto.com/">CARTO</a>',
subdomains: 'abcd',
maxZoom: 19
}).addTo(map);

desktopToggle.addEventListener("click", () => {
  desktopOpen = !desktopOpen;
  updatePanel();
});
mobileToggle.addEventListener("click", () => {
  mobileOpen = !mobileOpen;
  updatePanel();
});
overlay.addEventListener("click", () => {
  mobileOpen = false;
  updatePanel();
});
mobile.addEventListener("change", updatePanel);
map.getContainer().addEventListener("transitionend", (event) => {
  if (event.propertyName === "left") map.invalidateSize({ pan: false });
});
updatePanel();

search.addEventListener("submit", (event) => {
  event.preventDefault();
  const layer = byHandle.get(handle.value.trim());
  if (layer) select(layer, true);
  else status.textContent = "No matching HANDLE in the three-mile dataset.";
});

async function load() {
  const response = await fetch("./parcels.geojson");
  if (!response.ok) throw new Error(`Parcel data returned HTTP ${response.status}`);
  const layer = L.geoJSON(await response.json(), {
    style,
    onEachFeature(feature, shape) {
      byHandle.set(feature.properties.HANDLE, shape);
      shape.on("click", () => select(shape, false));
    },
  }).addTo(map);
  map.fitBounds(layer.getBounds(), { padding: [20, 20] });
  status.textContent = `${byHandle.size.toLocaleString("en-US")} parcels loaded`;
  search.querySelector("button").disabled = false;
}

load().catch((error) => {
  status.textContent = "Could not load parcel data. Open the map from a web server and try again.";
  console.error(error);
});
