#!/bin/bash
# =====================================================
# 2-Node MetroCluster Deployment Script
# Deploys: DRBD SyncMirror + LVM + iSCSI + Pacemaker HA
# Run on EITHER node after DRBD/LVM setup
# =====================================================

set -e  # Exit on any error

# CONFIGURATION - EDIT THESE VALUES
CLUSTER_NAME="debian"
NODE1="n1"
NODE2="n2"
NODE1_IP="192.168.1.10"
NODE2_IP="192.168.1.11"
VIP_IP="192.168.1.100/24"
DRBD_RESOURCE="ha-storage"
VG_NAME="vg-ha"
LV_NAME="lun1"
LV_SIZE="10G"
IQN="iqn.2025-12.college:ha.lun1"

echo "🚀 Deploying 2-Node MetroCluster: $CLUSTER_NAME"
echo "Nodes: $NODE1($NODE1_IP) ↔ $NODE2($NODE2_IP)"
echo "VIP: $VIP_IP | DRBD: $DRBD_RESOURCE | VG: $VG_NAME/$LV_NAME"
echo "================================================================"

# 1. LAB SAFETY - Disable STONITH (Production: configure real STONITH!)
sudo pcs property set stonith-enabled=false
sudo pcs property set no-quorum-policy=ignore

# 2. DRBD Resources (Mirrored Aggregate)
echo "📦 Creating DRBD HA resource..."
sudo pcs resource create drbd-ha ocf:heartbeat:drbd \
    drbd_resource="$DRBD_RESOURCE" \
    op monitor interval=60s \
    op promote timeout=120s \
    op demote timeout=120s

sudo pcs resource promotable drbd-ha masters=1

# 3. LVM Volume Group
echo "💾 Creating LVM resource..."
sudo pcs resource create vg-ha LVM vg="$VG_NAME" \
    op monitor interval=30s

# 4. Virtual IP (Floating iSCSI portal)
echo "🌐 Creating Virtual IP..."
sudo pcs resource create vip ocf:heartbeat:IPaddr2 \
    ip="$VIP_IP" \
    op monitor interval=30s

# 5. iSCSI Target
echo "🎯 Creating iSCSI Target..."
sudo pcs resource create iqn-target ocf:heartbeat:iSCSITarget \
    iqn="$IQN" \
    portal_ip="0.0.0.0" \
    op monitor interval=30s

# 6. iSCSI LUN
echo "💿 Creating iSCSI LUN..."
sudo pcs resource create lun1 ocf:heartbeat:iSCSILun \
    target_iqn="$IQN" \
    lun_id=0 \
    path="/dev/$VG_NAME/$LV_NAME" \
    op monitor interval=30s

# 7. Group Resources
echo "🔗 Grouping resources..."
sudo pcs resource group add ha-group vip iqn-target lun1
sudo pcs resource group add storage-group drbd-ha vg-ha

# 8. Critical Constraints (Ordering + Colocation)
echo "⚙️  Setting constraints..."
sudo pcs constraint colocation add ha-group with master drbd-ha-master INFINITY
sudo pcs constraint order vg-ha then promote drbd-ha-master
sudo pcs constraint order promote drbd-ha-master then start ha-group
sudo pcs constraint order demote drbd-ha-master then stop vg-ha

# 9. Stick to nodes (optional - uncomment for node preference)
# sudo pcs constraint location ha-group prefers $NODE1

echo "✅ ========================================================="
echo "✅ 2-NODE METROCLUSTER DEPLOYED SUCCESSFULLY!"
echo "✅ ========================================================="
echo ""
echo "📊 Check Status:"
echo "   sudo pcs status"
echo "   sudo drbdadm status $DRBD_RESOURCE"
echo ""
echo "🧪 Test Client:"
echo "   iscsiadm -m discovery -t sendtargets -p 192.168.1.100"
echo "   iscsiadm -m node -T $IQN -p 192.168.1.100 -l"
echo ""
echo "🔄 Test Failover:"
echo "   sudo pcs resource move ha-group $NODE2  # Manual"
echo "   # OR: sudo pcs node standby $NODE1      # Automatic"
echo ""
echo "🌐 WebConsole: http://your-ip:8000"
