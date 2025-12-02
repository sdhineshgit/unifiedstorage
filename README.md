# unifiedstorage


# Mini MetroCluster WebConsole

### Prerequisites
- Ubuntu 22.04+ with sudo/root access
- Python 3.8+
- DRBD, LVM2, targetcli installed

### Install dependencies
sudo apt update
sudo apt install python3-pip python3-venv lvm2 drbd-utils targetcli-fb
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

**Architecture overview**
DRBD + LVM + iSCSI on Ubuntu 22.04 with Pacemaker/Corosync for automatic failover.

Site A (node1)          Site B (node2)  
┌─────────────────┐    ┌─────────────────┐

│Local Disk│    │ Local Disk      │

│ /dev/sdb        │◄──►│ /dev/sdb        │ ← DRBD sync replication

└─────┬───────────┘    └─────┬───────────┘
      │                       │
┌─────▼───────────┐    ┌─────▼───────────┐
│ DRBD /dev/drbd0 │    │ DRBD /dev/drbd0 │
└─────┬───────────┘    └─────┬───────────┘
      │                       │
┌─────▼───────────┐    ┌─────▼───────────┐
│ LVM VG "vg-ha"  │    │ LVM VG "vg-ha"  │
│ LV "lun1"       │    │ LV "lun1"       │
└─────┬───────────┘    └─────┬───────────┘
      │                       │
┌─────▼───────────┐    ┌─────▼───────────┐
│ iSCSI Target    │    │ iSCSI Target    │ ← Only active on one node
│ 192.168.1.100   │    │ (standby)       │ ← Floating VIP
└─────────────────┘    └─────────────────┘

