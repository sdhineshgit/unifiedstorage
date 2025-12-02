from flask import Flask, request, jsonify, render_template
import subprocess

app = Flask(__name__)

def run_cmd(cmd):
    """Run shell command and return (code, stdout, stderr)."""
    try:
        proc = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, '', 'Command timed out'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pvcreate', methods=['POST'])
def pvcreate():
    data = request.json
    device = data.get('device')
    if not device or not device.startswith('/dev/'):
        return jsonify({'error':'Invalid device path'}), 400
    code, out, err = run_cmd(f"sudo pvcreate {device}")
    if code != 0:
        return jsonify({'error': err}), 500
    return jsonify({'message': out})

@app.route('/vgcreate', methods=['POST'])
def vgcreate():
    data = request.json
    vgname = data.get('vgname')
    devices = data.get('devices', [])
    if not vgname or not devices:
        return jsonify({'error':'vgname and devices are required'}), 400
    devlist = ' '.join(devices)
    code, out, err = run_cmd(f"sudo vgcreate {vgname} {devlist}")
    if code != 0:
        return jsonify({'error': err}), 500
    return jsonify({'message': out})

@app.route('/lvcreate', methods=['POST'])
def lvcreate():
    data = request.json
    vgname = data.get('vgname')
    lvname = data.get('lvname')
    size = data.get('size')  # e.g., '5G'
    if not vgname or not lvname or not size:
        return jsonify({'error':'vgname, lvname, and size are required'}), 400
    code, out, err = run_cmd(f"sudo lvcreate -L {size} -n {lvname} {vgname}")
    if code != 0:
        return jsonify({'error': err}), 500
    return jsonify({'message': out})

@app.route('/drbd-up', methods=['POST'])
def drbd_up():
    data = request.json
    resource = data.get('resource')
    if not resource:
        return jsonify({'error': 'resource name required'}), 400
    code, out, err = run_cmd(f"sudo drbdadm up {resource}")
    if code != 0:
        return jsonify({'error': err}), 500
    return jsonify({'message': out})

@app.route('/iscsi-create', methods=['POST'])
def iscsi_create():
    data = request.json
    iqn = data.get('iqn')
    backing_dev = data.get('backing_dev')  # e.g. /dev/vgname/lvname
    portal_ip = data.get('portal_ip', '0.0.0.0')
    lun_id = data.get('lun_id', 0)
    if not iqn or not backing_dev:
        return jsonify({'error':'iqn and backing_dev required'}), 400

    cmds = [
        f"sudo targetcli /iscsi create {iqn}",
        f"sudo targetcli /iscsi/{iqn}/tpg1/portals create {portal_ip}",
        f"sudo targetcli /backstores/block create name={iqn.split(':')[-1]} dev={backing_dev}",
        f"sudo targetcli /iscsi/{iqn}/tpg1/luns create /backstores/block/{iqn.split(':')[-1]}",
        "sudo targetcli saveconfig"
    ]
    for c in cmds:
        code, out, err = run_cmd(c)
        if code != 0:
            return jsonify({'error': f"Command `{c}` failed: {err}"}), 500
    return jsonify({'message': 'iSCSI target and LUN created successfully'})

@app.route('/list-lvs/<vgname>', methods=['GET'])
def list_lvs(vgname):
    """List logical volumes in a volume group"""
    code, out, err = run_cmd(f"sudo lvs --noheadings -o lv_name,lv_size {vgname}")
    if code != 0:
        return jsonify({'error': err}), 500
    lvs = []
    for line in out.strip().split('\n'):
        parts = line.strip().split()
        if len(parts) >= 2:
            lvs.append({'name': parts[0], 'size': parts[1]})
    return jsonify({'lvs': lvs})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
