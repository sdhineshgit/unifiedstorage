# unifiedstorage

DRBD + LVM + iSCSI on Ubuntu 22.04 with Pacemaker/Corosync for automatic failover.

Site A (node1)          Site B (node2)  
┌─────────────────┐    ┌─────────────────┐
│ Local Disk      │    │ Local Disk      │
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
