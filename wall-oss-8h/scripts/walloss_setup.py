import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
for i in range(6):
    try:
        c.connect('192.168.1.217', username='nvidia', password='nvidia', timeout=15); break
    except Exception as e:
        print('retry', i, e); time.sleep(4)

GEN = r'''
import re
src=open('/home/nvidia/runs/libero_ft.yml').read()
def mk(name, steps, save_int, save_path, epoch, warm):
    s=src
    s=re.sub(r'num_epoch:\s*\d+', 'num_epoch: %d'%epoch, s)
    s=re.sub(r'num_training_steps:\s*\d+', 'num_training_steps: %d'%steps, s)
    s=re.sub(r'num_warmup_steps:\s*\d+', 'num_warmup_steps: %d'%warm, s)
    s=re.sub(r'save_interval:\s*\d+', 'save_interval: %d'%save_int, s)
    s=re.sub(r'log_name:\s*\S+', 'log_name: %s'%name, s)
    s=re.sub(r'save_path:\s*\S+', 'save_path: %s'%save_path, s)
    open('/home/nvidia/runs/%s.yml'%name,'w').write(s)
mk('walloss_8h', 4200, 2000, '/home/nvidia/runs/walloss_8h', 10, 100)
mk('walloss_smoke', 20, 9999999, '/home/nvidia/runs/walloss_smoke', 1, 10)
print('OK wrote ymls')
for l in open('/home/nvidia/runs/walloss_smoke.yml').read().splitlines():
    if any(k in l for k in ['num_training_steps','save_interval','save_path','log_name']):
        print(l)
'''
i, o, e = c.exec_command('python3 - <<PYEOF\n' + GEN + '\nPYEOF', timeout=40)
print(o.read().decode()); print('ERR', e.read().decode()[:300])

SMOKE_SH = '''#!/bin/bash
set -u
export PATH="$HOME/.local/bin:$PATH"
export CUDA_HOME=/usr/local/cuda-13
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=8
source "$HOME/wallx-env/bin/activate"
cd "$HOME/wall-x"
echo "[$(date -Is)] SMOKE START"
free -g | sed -n 2p
nice -n 10 taskset -c 0-15 torchrun --standalone --nnodes=1 --nproc_per_node=1 wall_x/trainer/fsdp_trainer/train_fsdp.py --config "$HOME/runs/walloss_smoke.yml"
echo "[$(date -Is)] SMOKE EXIT=$?"
'''
sf = '/home/nvidia/run_walloss_smoke.sh'
sftp = c.open_sftp()
with sftp.file(sf, 'w') as f:
    f.write(SMOKE_SH)
sftp.close()
i, o, e = c.exec_command('chmod +x ' + sf + ' && echo chmod-ok', timeout=20); print(o.read().decode())

launch = 'cd /home/nvidia && setsid nohup bash /home/nvidia/run_walloss_smoke.sh > /home/nvidia/runs/walloss_smoke.log 2>&1 < /dev/null & echo PID=$!'
i, o, e = c.exec_command(launch, timeout=30); print('launch:', o.read().decode().strip())
time.sleep(12)
i, o, e = c.exec_command('tail -15 /home/nvidia/runs/walloss_smoke.log 2>&1', timeout=20)
print('--- tail ---'); print(o.read().decode())
c.close()
