# 常用操作入口。Windows 无 make 时直接用 `python -m ...` 等价命令。
PY ?= python

.PHONY: help install test demo demo-seed7 record qc all clean

help:
	@echo "make install    安装依赖"
	@echo "make test       跑单元测试"
	@echo "make demo       跑仿真演示（生成 out/demo.gif 等）"
	@echo "make record     采集示教数据到 data/raw（仿真演练 + 立即质检）"
	@echo "make qc         对 data/raw 做质检"
	@echo "make all        test + demo + record + qc"

install:
	$(PY) -m pip install -r requirements.txt

test:
	$(PY) -m pytest -q

demo:
	$(PY) -m sim.run_sim

demo-seed7:
	$(PY) -m sim.run_sim --seed 7 --out out/seed7

record:
	$(PY) -m scripts.record_episode --out data/raw --episodes 3 --seed 1 --min-frames 4 --qc

qc:
	$(PY) -m scripts.check_dataset --root data/raw --min-episodes 10

all: test demo record qc

clean:
	rm -rf out/*.gif out/*.png out/*.jsonl out/qc_report.json
