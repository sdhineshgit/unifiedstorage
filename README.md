# unifiedstorage


# 🚀 MetroCluster WebConsole - Complete Deployment

## Prerequisites
Ubuntu 22.04+ with DRBD/LVM/iSCSI/Pacemaker installed

## 1. Install System Dependencies
sudo apt update

sudo apt install -y python3-pip python3-venv lvm2 drbd-utils targetcli-fb pacemaker corosync pcs resource-agents fence-agents open-iscsi


## 2. Setup Python Environment
cd metrocluster-webconsole

python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt


## 3. Configure Sudo (Critical!)
sudo vi -f /etc/sudoers.d/webconsole

Add:

www-data ALL=(ALL) NOPASSWD:
/sbin/pvcreate, /sbin/vgcreate, /sbin/lvcreate,
/sbin/vgs, /sbin/lvs, /usr/sbin/drbdadm,
/usr/bin/targetcli, /usr/bin/pcs, /usr/sbin/crm


## 4. Fix Permissions
sudo chown -R www-data:www-data /path/to/metrocluster-webconsole

sudo chmod +x app.py


## 5. Run Development Server
source venv/bin/activate

sudo -u www-data python app.py


## 6. Production Deployment (Systemd)
Create `/etc/systemd/system/webconsole.service`:

[Unit]

Description=MetroCluster WebConsole

After=network.target

[Service]

User=www-data

WorkingDirectory=/path/to/metrocluster-webconsole

ExecStart=/path/to/metrocluster-webconsole/venv/bin/python app.py

Restart=always

[Install]

WantedBy=multi-user.target


sudo systemctl daemon-reload
sudo systemctl enable webconsole
sudo systemctl start webconsole


## 7. Access
- **URL**: http://your-server:8000
- **Credentials**: admin / metro123

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

