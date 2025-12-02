from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import subprocess
import re
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-super-secret-key-change-in-production'

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id):
        self.id = id

# Hardcoded user (replace with database in production)
USERS = {'admin': {'password': 'metro123'}}

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

def safe_run_cmd(cmd, timeout=30):
    """Secure command execution with validation and timeout."""
    try:
        # Basic command validation
        if any(dangerous in cmd for dangerous in [';', '&', '|', '`', '$(']):
            return 1, '', 'Command injection detected'
        
        proc = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE, text=True, timeout=timeout)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, '', f'Command timed out after {timeout}s'
    except Exception as e:
        return 1, '', f'Execution error: {str(e)}'

def validate_device(device):
    """Validate block device path."""
    if not re.match(r'^/dev/[a-zA-Z0-9/]+$', device):
        return False
    return True

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in USERS and USERS[username]['password'] == password:
            user = User(username)
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

# === LVM Management ===
@app.route('/api/pvcreate', methods=['POST'])
@login_required
def api_pvcreate():
    data = request.json
    device = data.get('device')
    if not validate_device(device):
        return jsonify({'error': 'Invalid device path'}), 400
    code, out, err = safe_run_cmd(f"sudo pvcreate -f {device}")
    if code != 0:
        return jsonify({'error': err}), 500
    return jsonify({'success': out})

@app.route('/api/vgcreate', methods=['POST'])
@login_required
def api_vgcreate():
    data = request.json
    vgname = data.get('vgname')
    devices = data.get('devices', [])
    
    if not re.match(r'^[a-zA-Z0-9-]+$', vgname):
        return jsonify({'error': 'Invalid VG name'}), 400
    
    valid_devices = [d for d in devices if validate_device(d)]
    if len(valid_devices) != len(devices):
        return jsonify({'error': 'Invalid device paths'}), 400
    
    devlist = ' '.join(valid_devices)
    code, out, err = safe_run_cmd(f"sudo vgcreate {vgname} {devlist}")
    if code != 0:
        return jsonify({'error': err}), 500
    return jsonify({'success': out})

@app.route('/api/lvcreate', methods=['POST'])
@login_required
def api_lvcreate():
    data = request.json
    vgname = data.get('vgname')
    lvname = data.get('lvname')
    size = data.get('size')
    
    if not all([vgname, lvname, size]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    code, out, err = safe_run_cmd(f"sudo lvcreate -L {size} -n {lvname} {vgname}")
    if code != 0:
        return jsonify({'error': err}), 500
    return jsonify({'success': out})

@app.route('/api/list-volumes', methods=['GET'])
@login_required
def api_list_volumes():
    code, out, err = safe_run_cmd("sudo vgs --noheadings --reportformat=json")
    if code != 0:
        return jsonify({'error': err}), 500
    
    code2, out2, err2 = safe_run_cmd("sudo lvs --noheadings --reportformat=json")
    return jsonify({
        'vgs': json.loads(out) if out else [],
        'lvs': json.loads(out2) if out2 else []
    })

# === DRBD Management ===
@app.route('/api/drbd-status', methods=['GET'])
@login_required
def api_drbd_status():
    code, out, err = safe_run_cmd("sudo drbdadm status --verbose")
    if code != 0:
        code, out, err = safe_run_cmd("cat /proc/drbd")
    return jsonify({'raw': out, 'error': err if code != 0 else None})

@app.route('/api/drbd-create', methods=['POST'])
@login_required
def api_drbd_create():
    data = request.json
    resource = data.get('resource')
    node1_ip = data.get('node1_ip')
    node2_ip = data.get('node2_ip')
    
    drbd_config = f"""
resource {resource} {{
  protocol C;
  device /dev/drbd0;
  disk /dev/sdb1;
  meta-disk internal;
  on node1 {{ address {node1_ip}:7790; }}
  on node2 {{ address {node2_ip}:7790; }}
}}
"""
    with open(f"/etc/drbd.d/{resource}.res", "w") as f:
        f.write(drbd_config)
    
    code, out, err = safe_run_cmd(f"sudo drbdadm create-md {resource}")
    if code != 0:
        return jsonify({'error': err}), 500
    
    code, out, err = safe_run_cmd(f"sudo drbdadm up {resource}")
    return jsonify({'success': out})

@app.route('/api/drbd-primary', methods=['POST'])
@login_required
def api_drbd_primary():
    resource = request.json.get('resource', 'ha-storage')
    code, out, err = safe_run_cmd(f"sudo drbdadm primary --force {resource}")
    if code != 0:
        return jsonify({'error': err}), 500
    return jsonify({'success': out})

# === iSCSI Management ===
@app.route('/api/iscsi-create', methods=['POST'])
@login_required
def api_iscsi_create():
    data = request.json
    iqn = data.get('iqn')
    backing_dev = data.get('backing_dev')
    portal_ip = data.get('portal_ip', '0.0.0.0')
    
    if not validate_device(backing_dev):
        return jsonify({'error': 'Invalid backing device'}), 400
    
    lun_name = iqn.split(':')[-1]
    cmds = [
        f"sudo targetcli /iscsi create {iqn}",
        f"sudo targetcli /iscsi/{iqn}/tpg1/portals create {portal_ip}",
        f"sudo targetcli /backstores/block create name={lun_name} dev={backing_dev}",
        f"sudo targetcli /iscsi/{iqn}/tpg1/luns create /backstores/block/{lun_name}",
        "sudo targetcli saveconfig"
    ]
    
    for cmd in cmds:
        code, _, err = safe_run_cmd(cmd)
        if code != 0:
            return jsonify({'error': f'{cmd}: {err}'}), 500
    
    return jsonify({'success': 'iSCSI target created'})

@app.route('/api/iscsi-list', methods=['GET'])
@login_required
def api_iscsi_list():
    code, out, err = safe_run_cmd("sudo targetcli /iscsi ls")
    return jsonify({'targets': out})

# === Cluster Status ===
@app.route('/api/cluster-status', methods=['GET'])
@login_required
def api_cluster_status():
    code, out, err = safe_run_cmd("sudo pcs status --full")
    if code != 0:
        code, out, err = safe_run_cmd("sudo crm status full")
    return jsonify({'status
