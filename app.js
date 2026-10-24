const stations = [
  { id: 1, name: 'Mohan Babu University', area: 'Sree Sainath Nagar', status: 'safe', lat: 13.6269, lng: 79.3557, quality: '92%', pH: '7.2', usage: '1,240 L' },
  { id: 2, name: 'Tirupati Railway Station', area: 'Central Tirupati', status: 'safe', lat: 13.6277, lng: 79.4170, quality: '89%', pH: '7.4', usage: '980 L' },
  { id: 3, name: 'Sri Padmavathi Intake', area: 'South Tirupati', status: 'warning', lat: 13.6100, lng: 79.4210, quality: '74%', pH: '6.9', usage: '1,420 L' },
  { id: 4, name: 'Renigunta Junction', area: 'Renigunta Zone', status: 'safe', lat: 13.6518, lng: 79.5120, quality: '94%', pH: '7.1', usage: '760 L' },
  { id: 5, name: 'MR Palli Reservoir', area: 'North Tirupati', status: 'danger', lat: 13.6465, lng: 79.4203, quality: '58%', pH: '6.4', usage: '1,680 L' },
  { id: 6, name: 'SV University', area: 'Balaji Nagar', status: 'safe', lat: 13.6304, lng: 79.4072, quality: '91%', pH: '7.3', usage: '920 L' },
  { id: 7, name: 'Kapila Theertham', area: 'Alipiri Zone', status: 'warning', lat: 13.6835, lng: 79.3485, quality: '71%', pH: '7.0', usage: '1,510 L' },
  { id: 8, name: 'Tiruchanur Supply', area: 'East Tirupati', status: 'safe', lat: 13.6085, lng: 79.4500, quality: '87%', pH: '7.5', usage: '810 L' }
];

let currentRole = 'admin';

const map = L.map('map', { zoomControl: false }).setView([13.6288, 79.4192], 13);
L.control.zoom({ position: 'bottomright' }).addTo(map);

const roadMap = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 20,
  attribution: '&copy; OpenStreetMap contributors'
});
const satelliteMap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
  maxZoom: 20,
  attribution: 'Tiles &copy; Esri'
});
const satelliteLabels = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png', {
  maxZoom: 20,
  attribution: '&copy; OpenStreetMap &copy; CARTO'
});

satelliteMap.addTo(map);
satelliteLabels.addTo(map);
const baseMaps = {
  'Satellite view': satelliteMap,
  'Road and buildings': roadMap
};
L.control.layers(baseMaps, null, { position: 'topright', collapsed: true }).addTo(map);

map.on('baselayerchange', event => {
  if (event.name === 'Satellite view') satelliteLabels.addTo(map);
  else map.removeLayer(satelliteLabels);
});

const highUsageZones = L.layerGroup([
  L.polygon([
    [13.6155, 79.3430], [13.6420, 79.3430],
    [13.6420, 79.3670], [13.6155, 79.3670]
  ], { color: '#f04f4f', weight: 2, fillColor: '#f04f4f', fillOpacity: 0.16 }),
  L.polygon([
    [13.6200, 79.3950], [13.6550, 79.3950],
    [13.6550, 79.4270], [13.6200, 79.4270]
  ], { color: '#e6a12e', weight: 2, fillColor: '#e6a12e', fillOpacity: 0.14 }),
  L.polygon([
    [13.6420, 79.5000], [13.6740, 79.5000],
    [13.6740, 79.5250], [13.6420, 79.5250]
  ], { color: '#e6a12e', weight: 2, fillColor: '#e6a12e', fillOpacity: 0.14 })
]).addTo(map);

highUsageZones.eachLayer(layer => {
  layer.bindTooltip('High water usage area', { sticky: true, direction: 'center', className: 'usage-tooltip' });
});

const placeLabels = L.layerGroup([
  L.marker([13.6288, 79.4192], {
    interactive: false,
    icon: L.divIcon({ className: 'place-label-wrap', html: '<span class="place-label">Tirupati</span>', iconSize: [88, 26], iconAnchor: [44, 13] })
  }),
  L.marker([13.6269, 79.3557], {
    interactive: false,
    icon: L.divIcon({ className: 'place-label-wrap', html: '<span class="place-label college-label">Mohan Babu University</span>', iconSize: [180, 26], iconAnchor: [90, 13] })
  })
]).addTo(map);

const markerLayer = L.layerGroup().addTo(map);
let activeFilter = 'all';
let activeMarkers = new Map();

function statusLabel(status) {
  return status === 'safe' ? 'Safe' : status === 'warning' ? 'Watch' : 'Alert';
}

function stationIcon(status) {
  return L.divIcon({
    className: '',
    html: `<div class="marker-pin ${status}"><span></span></div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 29],
    popupAnchor: [0, -27]
  });
}

function renderMarkers() {
  markerLayer.clearLayers();
  activeMarkers.clear();
  stations.forEach(station => {
    if (activeFilter !== 'all' && station.status !== activeFilter) return;
    const marker = L.marker([station.lat, station.lng], { icon: stationIcon(station.status) }).addTo(markerLayer);
    marker.bindPopup(`<h3 class="popup-title">${station.name}</h3><p class="popup-meta">${statusLabel(station.status)} · Water quality ${station.quality}</p><p class="popup-meta">pH ${station.pH} · ${station.area}</p>`);
    activeMarkers.set(station.id, marker);
  });
}

function stationDropIcon(status) {
  const paths = status === 'safe'
    ? '<path d="M12 2.8S6 9.4 6 14a6 6 0 0 0 12 0c0-4.6-6-11.2-6-11.2Z"/><path d="m9 14 2 2 4-5"/>'
    : '<path d="M12 2.8S6 9.4 6 14a6 6 0 0 0 12 0c0-4.6-6-11.2-6-11.2Z"/><path d="M12 9v4m0 3h.01"/>';
  return `<svg viewBox="0 0 24 24" aria-hidden="true">${paths}</svg>`;
}

function renderList() {
  const query = document.getElementById('searchInput').value.toLowerCase().trim();
  const stationList = document.getElementById('stationList');
  const visible = stations.filter(station => {
    const matchesFilter = activeFilter === 'all' || station.status === activeFilter;
    const matchesQuery = `${station.name} ${station.area}`.toLowerCase().includes(query);
    return matchesFilter && matchesQuery;
  });

  stationList.innerHTML = visible.map(station => `
    <button class="station-card" data-id="${station.id}" type="button">
      <span class="status-ring ${station.status}">${stationDropIcon(station.status)}</span>
      <span><strong class="station-name">${station.name}</strong><p class="station-meta">${station.area}</p></span>
      <span class="station-value"><strong>${currentRole === 'user' ? station.usage || '850 L' : station.quality}</strong><span>${currentRole === 'user' ? 'used today' : 'quality'}</span></span>
    </button>
  `).join('');

  stationList.querySelectorAll('.station-card').forEach(card => {
    card.addEventListener('click', () => {
      document.querySelectorAll('.station-card').forEach(item => item.classList.remove('selected'));
      card.classList.add('selected');
      const station = stations.find(item => item.id === Number(card.dataset.id));
      map.flyTo([station.lat, station.lng], 14, { duration: 0.8 });
      activeMarkers.get(station.id)?.openPopup();
    });
  });
}

function refresh() {
  renderMarkers();
  renderList();
}

refresh();
setRole('admin');

document.querySelectorAll('.filter').forEach(button => {
  button.addEventListener('click', () => {
    document.querySelectorAll('.filter').forEach(item => item.classList.remove('active'));
    button.classList.add('active');
    activeFilter = button.dataset.filter;
    refresh();
  });
});

document.getElementById('searchInput').addEventListener('input', renderList);

function setRole(role) {
  currentRole = role;
  document.body.classList.toggle('user-mode', role === 'user');
  document.querySelectorAll('.role-button').forEach(button => {
    button.classList.toggle('active', button.dataset.role === role);
  });

  document.querySelector('.sidebar-heading h1').textContent = role === 'admin' ? 'Monitoring map' : 'Water usage';
  document.querySelector('.sidebar-heading .eyebrow').textContent = role === 'admin' ? 'Water network' : 'Mohan Babu University';
  document.getElementById('reportButton').innerHTML = role === 'admin'
    ? '<span aria-hidden="true">+</span> Report issue'
    : '<span aria-hidden="true">+</span> Report leakage';

  document.querySelectorAll('.admin-only-option').forEach(option => {
    option.hidden = role === 'user';
    option.disabled = role === 'user';
  });
  document.getElementById('issueType').value = role === 'user' ? 'Leak' : 'Contamination';

  if (role === 'user') {
    map.flyTo([13.6269, 79.3557], 15, { duration: 0.8 });
    showToast('User view: monitoring data and leakage reports');
  } else {
    showToast('Admin view: full monitoring controls enabled');
  }
}

document.querySelectorAll('.role-button').forEach(button => {
  button.addEventListener('click', () => setRole(button.dataset.role));
});

document.querySelectorAll('.nav-link').forEach(button => {
  button.addEventListener('click', () => {
    document.querySelectorAll('.nav-link').forEach(item => item.classList.remove('active'));
    button.classList.add('active');
    if (button.textContent.trim() === 'Reports' && currentRole === 'admin') {
      const reports = JSON.parse(localStorage.getItem('aquaguardReports') || '[]');
      showToast(reports.length ? `${reports.length} report(s) pending review` : 'No new reports');
    } else if (button.textContent.trim() === 'Analytics' && currentRole === 'admin') {
      showToast('Network summary: 8 stations, 5 safe, 2 watch, 1 alert');
    }
  });
});

const reportDialog = document.getElementById('reportDialog');
function openReport() { reportDialog.showModal(); }
document.getElementById('openReportButton').addEventListener('click', openReport);
document.getElementById('reportButton').addEventListener('click', openReport);
document.getElementById('closeReportButton').addEventListener('click', () => reportDialog.close());

function showToast(message) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.add('show');
  window.setTimeout(() => toast.classList.remove('show'), 2800);
}

document.getElementById('reportForm').addEventListener('submit', event => {
  event.preventDefault();
  const lat = Number(document.getElementById('latitude').value);
  const lng = Number(document.getElementById('longitude').value);
  const issue = currentRole === 'user' ? 'Leak' : document.getElementById('issueType').value;
  const details = document.getElementById('details').value.trim();
  if (!details || !Number.isFinite(lat) || !Number.isFinite(lng)) return;

  const reportMarker = L.marker([lat, lng], { icon: stationIcon('danger') }).addTo(markerLayer);
  reportMarker.bindPopup(`<h3 class="popup-title">${issue}</h3><p class="popup-meta">Community report · Awaiting review</p><p class="popup-meta">${details}</p>`).openPopup();
  map.flyTo([lat, lng], 14, { duration: 0.8 });
  const report = {
    id: Date.now(),
    role: currentRole,
    issue,
    details,
    lat,
    lng,
    createdAt: new Date().toISOString(),
    status: 'Pending'
  };
  const savedReports = JSON.parse(localStorage.getItem('aquaguardReports') || '[]');
  savedReports.unshift(report);
  localStorage.setItem('aquaguardReports', JSON.stringify(savedReports));

  reportDialog.close();
  event.target.reset();
  document.getElementById('issueType').value = currentRole === 'user' ? 'Leak' : 'Contamination';
  showToast(currentRole === 'user' ? 'Leakage report sent for review' : 'Report submitted and sent for review');
});

document.getElementById('locateButton').addEventListener('click', () => {
  if (!navigator.geolocation) {
    showToast('Location services are not supported');
    return;
  }
  navigator.geolocation.getCurrentPosition(position => {
    const { latitude, longitude } = position.coords;
    map.flyTo([latitude, longitude], 14, { duration: 0.8 });
    document.getElementById('latitude').value = latitude.toFixed(5);
    document.getElementById('longitude').value = longitude.toFixed(5);
    showToast('Moved to your location');
  }, () => showToast('Unable to access your location'), { enableHighAccuracy: true });
});
