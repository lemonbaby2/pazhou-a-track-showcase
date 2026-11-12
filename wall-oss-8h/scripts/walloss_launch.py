import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
for i in range(6):
    try:
        c.connect('192.168.1.217', username='nvidia', password='nvidia', timeout=15); break
    except Exception as e:
        print('retry', i, e); time.sleep(4)

# 1) 调整步数：4000 步（≈7.7h）且是 save_interval=2000 的倍数，保证最终权重落盘
i, o, e = c.exec_command(
    "sed -i 's/num_training_steps: 4200/num_training_steps: 4000/' /home/nvidia/runs/walloss_8h.yml && "
    "grep -E 'num_training_steps|save_interval|save_path|num_epoch' /home/nvidia/runs/walloss_8h.yml",
    timeout=30)
print(o.read().decode()); print('ERR', e.read().decode()[:200])

# 2) 写 8h 启动脚本
SH = '''#!/bin/bash
set -u
export PATH="$HOME/.local/bin:$PATH"
export CUDA_HOME=/usr/local/cuda-13
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=8
source "$HOME/wallx-env/bin/activate"
cd "$HOME/wall-x"
echo "[$(date -Is)] 8H TRAIN START"
free -g | sed -n 2p
nice -n 10 taskset -c 0-15 torchrun --standalone --nnodes=1 --nproc_per_node=1 wall_x/trainer/fsdp_trainer/train_fsdp.py --config "$HOME/runs/walloss_8h.yml"
echo "[$(date -Is)] 8H TRAIN EXIT=$?"
'''
sf = '/home/nvidia/run_walloss_8h.sh'
sftp = c.open_sftp()
with sftp.file(sf, 'w') as f:
    f.write(SH)
sftp.close()
i, o, e = c.exec_command('chmod +x ' + sf + ' && echo chmod-ok', timeout=20); print(o.read().decode())

# 3) 脱离会话启动（不读 stdout，避免通道阻塞）
launch = 'cd /home/nvidia && setsid nohup bash /home/nvidia/run_walloss_8h.sh > /home/nvidia/runs/walloss_8h.log 2>&1 < /dev/null &'
try:
    i, o, e = c.exec_command(launch, timeout=12)
    o.channel.settimeout(8)
    print('launch raw:', o.read().decode(errors='replace')[:100])
except Exception as ex:
    print('launch channel note:', type(ex).__name__)

time.sleep(15)
i, o, e = c.exec_command('ps -ef | grep train_fsdp | grep -v grep | head -3; echo ===; tail -6 /home/nvidia/runs/walloss_8h.log 2>&1', timeout=25)
print('--- status ---'); print(o.read().decode('utf-8', 'replace'))
c.close()
