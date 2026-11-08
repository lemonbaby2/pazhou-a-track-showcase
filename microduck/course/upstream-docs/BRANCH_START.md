# 当前分支：MicroDuck Task2

这是 `microduck-task2` 提交分支，核心交付位于 [`task2/`](task2/)。

## 启动浏览器仿真

```bash
python datawhale_microduck/task2/official_materials/serve_mjswan.py \
  --directory /home/lizp/microduck-task2/dist/microduck \
  --host 127.0.0.1 \
  --port 8092
```

浏览器打开 `http://127.0.0.1:8092/?scene=duck&policy=walk`。完整 Notebook、48.8 秒三次扰动录像、关键帧和机器可读报告见 [`task2/README.md`](task2/README.md)。

本结果是浏览器 MuJoCo 中的定性 smoke test，不等同于标准化鲁棒性基准或真机验证。依赖、复现方式与来源见 [`START_HERE.md`](START_HERE.md)。

