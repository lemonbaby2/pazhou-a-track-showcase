import paramiko, re, time, sys

def main():
    c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    for i in range(5):
        try:
            c.connect('192.168.1.217', username='nvidia', password='nvidia', timeout=15); break
        except Exception as e:
            if i == 4: print('SSH FAIL:', e); return
            time.sleep(3)
    i, o, e = c.exec_command(
        "grep -E 'FSDP Train' /home/nvidia/runs/walloss_8h.log | tail -40; "
        "echo '@@@'; ps -ef | grep train_fsdp | grep -v grep | wc -l; "
        "echo '@@@'; free -g | sed -n 2p; "
        "echo '@@@'; nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader; "
        "echo '@@@'; ls /home/nvidia/runs/walloss_8h 2>/dev/null; "
        "echo '@@@'; df -h /home/nvidia | tail -1; "
        "echo '@@@'; grep -c 'EXIT=' /home/nvidia/runs/walloss_8h.log 2>/dev/null",
        timeout=40)
    out = o.read().decode('utf-8', 'replace')
    c.close()
    parts = out.split('@@@')
    lines = parts[0].strip().splitlines()
    steps = []
    for ln in lines:
        m = re.search(r"Step (\d+): \{'flow_loss': ([\d.]+).*?'grad_norm': ([\d.]+), 'lr': ([\d.eE+-]+)", ln)
        if m:
            steps.append((int(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))))
    proc = parts[1].strip()
    mem = parts[2].strip()
    gpu = parts[3].strip()
    ckpts = parts[4].strip().replace('\n', ' ')
    disk = parts[5].strip()
    exited = parts[6].strip()
    print('=== Wall-OSS-0.5 8h 训练进度 ===')
    if steps:
        cur = steps[-1][0]
        losses = [s[1] for s in steps]
        print(f'当前步: {cur}/4000  剩余约 {4000-cur} 步')
        print(f'最近 loss: {steps[-1][1]:.4f}  近40步min: {min(losses):.4f}  max: {max(losses):.4f}')
        print(f'grad_norm: {steps[-1][2]:.2f}  lr: {steps[-1][3]:.2e}')
        # ETA at ~6.5s/step
        eta_min = (4000 - cur) * 6.5 / 60
        print(f'预计剩余: {eta_min/60:.1f} 小时')
    print(f'进程数: {proc} | GPU: {gpu}% | 内存: {mem}')
    print(f'checkpoint: {ckpts}')
    print(f'磁盘: {disk}')
    print(f'已结束: {"是" if exited not in ("0","") else "否(训练中)"}')

if __name__ == '__main__':
    main()
