import paramiko, time

c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
for i in range(8):
    try:
        c.connect('192.168.1.217', username='nvidia', password='nvidia', timeout=12); break
    except Exception as e:
        time.sleep(2)

# 1) 清旧中断 checkpoint；2) save_interval -> 4000（只存最终权重）
i, o, e = c.exec_command(
    "rm -rf /home/nvidia/runs/libero_ft/0_500; "
    "sed -i 's/save_interval: 2000/save_interval: 4000/' /home/nvidia/runs/walloss_8h.yml; "
    "sleep 3; df -h / | tail -1; "
    "grep -E 'num_training_steps|save_interval|save_path' /home/nvidia/runs/walloss_8h.yml",
    timeout=60)
print(o.read().decode()); print('ERR', e.read().decode()[:200])

# 2) 重启训练（覆盖旧日志）
launch = 'cd /home/nvidia && setsid nohup bash /home/nvidia/run_walloss_8h.sh > /home/nvidia/runs/walloss_8h.log 2>&1 < /dev/null &'
try:
    i, o, e = c.exec_command(launch, timeout=10)
    o.channel.settimeout(6)
    o.read()
except Exception as ex:
    print('launch note:', type(ex).__name__)

time.sleep(15)
i, o, e = c.exec_command(
    "df -h / | tail -1; echo ===PS===; ps -ef | grep train_fsdp | grep -v grep | wc -l; "
    "echo ===LOG===; tail -4 /home/nvidia/runs/walloss_8h.log 2>&1", timeout=30)
print('--- relaunch status ---'); print(o.read().decode('utf-8', 'replace'))
c.close()
