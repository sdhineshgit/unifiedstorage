// Auto-refresh status every 10s
setInterval(() => {
    loadDRBDStatus();
    loadClusterStatus();
    loadISCSI();
}, 10000);

// Load initial status
document.addEventListener('DOMContentLoaded', () => {
    loadDRBDStatus();
    loadClusterStatus();
    loadISCSI();
    loadVolumes();
});

// Tab switching
function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
    event.target.classList.add('active');
}

// API calls
async function apiCall(endpoint, data) {
    try {
        const res = await fetch(`/api${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return await res.json();
    } catch (e) {
        return { error: e.message };
    }
}

async function getApi(endpoint) {
    try {
        const res = await fetch(`/api${endpoint}`);
        return await res.json();
    } catch (e) {
        return { error: e.message };
    }
}

// LVM Functions
async function createPV() {
    const device = document.getElementById('pv-device').value;
    const result = await apiCall('/pvcreate', { device });
    document.getElementById('pv-result').textContent = JSON.stringify(result, null, 2);
}

async function createVG() {
    const vgname = document.getElementById('vg-name').value;
    const devices = document.getElementById('vg-devices').value.trim().split(/\s+/);
    const result = await apiCall('/vgcreate', { vgname, devices });
    document.getElementById('vg-result').textContent = JSON.stringify(result, null, 2);
}

async function createLV() {
    const vgname = document.getElementById('lv-vgname').value;
    const lvname = document.getElementById('lv-name').value;
    const size = document.getElementById('lv-size').value;
    const result = await apiCall('/lvcreate', { vgname, lvname, size });
    document.getElementById('lv-result').textContent = JSON.stringify(result, null, 2);
}

async function loadVolumes() {
    const data = await getApi('/list-volumes');
    document.getElementById('volumes-list').textContent = JSON.stringify(data, null, 2);
}

// DRBD Functions
async function loadDRBDStatus() {
    const data = await getApi('/drbd-status');
    document.getElementById('drbd-status').innerHTML = `<strong>DRBD:</strong> ${data.raw || data.error || 'Unknown'}`;
    document.getElementById('drbd-status-detail').textContent = data.raw || data.error;
}

async function drbdPrimary() {
    const resource = document.getElementById('drbd-resource').value;
    const result = await apiCall('/drbd-primary', { resource });
    document.getElementById('drbd-primary-result').textContent = JSON.stringify(result, null, 2);
}

// iSCSI Functions
async function createISCSI() {
    const iqn = document.getElementById('iscsi-iqn').value;
    const backing_dev = document.getElementById('iscsi-dev').value;
    const portal_ip = document.getElementById('iscsi-portal').value;
    const result = await apiCall('/iscsi-create', { iqn, backing_dev, portal_ip });
    document.getElementById('iscsi-result').textContent = JSON.stringify(result, null, 2);
}

async function loadISCSI() {
    const data = await getApi('/iscsi-list');
    document.getElementById('iscsi-status').innerHTML = `<strong>iSCSI:</strong> ${data.targets ? 'Active' : 'None'}`;
    document.getElementById('iscsi-list').textContent = data.targets || 'No targets';
}

// Cluster Functions
async function loadClusterStatus() {
    const data = await getApi('/cluster-status');
    document.getElementById('cluster-status').innerHTML = `<strong>Cluster:</strong> ${data.status ? 'OK' : 'Error'}`;
    document.getElementById('cluster-status-detail').textContent = data.status || data.error;
}

async function loadLogs() {
    const data = await getApi('/logs?limit=50');
    document.getElementById('logs').textContent = data.logs.join('\n');
}
