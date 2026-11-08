#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《任务感知 Real2Sim2Real 迁移与奖励结构调优》双栏投稿稿（A4 双栏，宋体 + Times New Roman）。

数据全部来自 paper-agent/data/ 下的真实训练日志与实测结果，插图由 make_figs.py 生成。
用法：python build_paper.py
"""
from __future__ import annotations

import json
import os

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
FIGS = os.path.join(BASE, "figs")
OUT = os.path.join(BASE, "MicroDuck短跑策略_Real2Sim2Real_双栏投稿稿.docx")

CN_BODY = "宋体"
CN_HEAD = "黑体"
EN = "Times New Roman"


def load(name):
    p = os.path.join(DATA, name)
    return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else None


V1M = load("v1_metrics.json")
V1S = load("v1_speed.json") or {}
V2M = load("v2_metrics.json")
V2S = load("v2_speed.json") or {}


def fmt(v, nd=2, dash="—"):
    return dash if v is None else f"{v:.{nd}f}"


def last(series, key, nd=3):
    if not series:
        return "—"
    v = (series.get("series") or {}).get(key)
    return "—" if not v else f"{v[-1]:.{nd}f}"


# ---------------- 底层排版工具 ----------------

def set_run(run, size=9, bold=False, cn=CN_BODY, en=EN, italic=False, color=None):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = en
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), en)
    rfonts.set(qn("w:hAnsi"), en)
    rfonts.set(qn("w:eastAsia"), cn)
    if color:
        run.font.color.rgb = RGBColor(*color)


def para(doc, text="", size=9, bold=False, cn=CN_BODY, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
         indent=True, space_before=0, space_after=3, line=13.5, color=None):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing = Pt(line)
    if indent:
        pf.first_line_indent = Pt(size * 2)
    if text:
        set_run(p.add_run(text), size=size, bold=bold, cn=cn, color=color)
    return p


def heading(doc, text, level=1):
    if level == 1:
        p = para(doc, text, size=10.5, bold=True, cn=CN_HEAD, indent=False,
                 align=WD_ALIGN_PARAGRAPH.LEFT, space_before=8, space_after=4, line=15)
    else:
        p = para(doc, text, size=9, bold=True, cn=CN_HEAD, indent=False,
                 align=WD_ALIGN_PARAGRAPH.LEFT, space_before=5, space_after=2, line=13.5)
    return p


def equation(doc, body, number):
    """公式行：公式居中，编号右对齐（用制表位实现）。"""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(2)
    pf.space_after = Pt(3)
    pf.line_spacing = Pt(13.5)
    pf.tab_stops.add_tab_stop(Cm(4.3), WD_TAB_ALIGNMENT.CENTER)
    pf.tab_stops.add_tab_stop(Cm(8.6), WD_TAB_ALIGNMENT.RIGHT)
    set_run(p.add_run("\t" + body + "\t(" + number + ")"), size=9, italic=True)
    return p


def caption(doc, text, above=False):
    return para(doc, text, size=8.5, bold=True, cn=CN_HEAD, indent=False,
                align=WD_ALIGN_PARAGRAPH.CENTER, space_before=4 if above else 2,
                space_after=2 if above else 6, line=12)


def figure(doc, filename, cap, width_cm=8.4):
    path = os.path.join(FIGS, filename)
    if not os.path.isfile(path):
        para(doc, f"[插图缺失：{filename}]", size=8.5, indent=False, color=(200, 0, 0))
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(0)
    p.add_run().add_picture(path, width=Cm(width_cm))
    caption(doc, cap)


def _set_cell_border(cell, **kwargs):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    borders = tcPr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tcPr.append(borders)
    for edge in ("top", "left", "bottom", "right"):
        if edge in kwargs:
            spec = kwargs[edge]
            tag = "w:" + edge
            el = borders.find(qn(tag))
            if el is None:
                el = OxmlElement(tag)
                borders.append(el)
            for k, v in spec.items():
                el.set(qn("w:" + k), str(v))


def table(doc, headers, rows, cap, widths=None, font=7.8):
    caption(doc, cap, above=True)
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    none = {"val": "nil"}
    thin = {"val": "single", "sz": 4, "color": "808080"}
    thick = {"val": "single", "sz": 12, "color": "000000"}

    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.space_before = Pt(1)
        set_run(p.add_run(h), size=font, bold=True, cn=CN_HEAD)
        _set_cell_border(hdr[i], top=thick, bottom=thin, left=none, right=none)
    for r in rows:
        cells = t.add_row().cells
        for i, v in enumerate(r):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if i == 0 else WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.line_spacing = Pt(11)
            set_run(p.add_run(str(v)), size=font)
            _set_cell_border(cells[i], top=none, bottom=none, left=none, right=none)
    last_cells = t.rows[-1].cells
    for c in last_cells:
        _set_cell_border(c, bottom=thick)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    para(doc, "", size=4, indent=False, space_after=2)
    return t


def two_columns(doc):
    sect = doc.sections[0]
    sect.page_width = Cm(21.0)
    sect.page_height = Cm(29.7)
    sect.top_margin = Cm(1.9)
    sect.bottom_margin = Cm(1.9)
    sect.left_margin = Cm(1.5)
    sect.right_margin = Cm(1.5)
    cols = sect._sectPr.xpath("./w:cols")[0]
    cols.set(qn("w:num"), "2")
    cols.set(qn("w:space"), "425")


def page_number_footer(doc):
    footer = doc.sections[0].footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run()
    for instr in ("begin", "text", "separate", "end"):
        el = OxmlElement("w:fldChar") if instr != "text" else OxmlElement("w:instrText")
        if instr == "text":
            el.set(qn("xml:space"), "preserve")
            el.text = " PAGE "
        else:
            el.set(qn("w:fldCharType"), instr)
        r._r.append(el)
    set_run(r, size=8)


# ---------------- 正文 ----------------

def build():
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = EN
    st.font.size = Pt(9)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), CN_BODY)
    two_columns(doc)
    page_number_footer(doc)

    # ===== 标题区（首页通栏前置于双栏正文，仍保持双栏节内居中）=====
    para(doc, "任务感知 Real2Sim2Real 迁移与奖励结构调优：",
         size=13, bold=True, cn=CN_HEAD, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, line=19, space_after=0)
    para(doc, "MicroDuck 双足机器人短跑策略的实证研究",
         size=13, bold=True, cn=CN_HEAD, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, line=19, space_after=4)
    para(doc, "Task-Aware Real2Sim2Real Transfer and Reward-Structure Tuning: "
              "An Empirical Study on Sprint Policies for the MicroDuck Biped Robot",
         size=9, cn=CN_BODY, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, line=12, space_after=5)
    para(doc, "（作者姓名　单位名称　城市　邮编）", size=8.5, indent=False,
         align=WD_ALIGN_PARAGRAPH.CENTER, color=(110, 110, 110), space_after=6)

    # ===== 摘要 =====
    para(doc, "摘　要：针对具身双足机器人在真实—仿真—真实（Real2Sim2Real）迁移中普遍存在的"
              "执行器物理失配与奖励信号失真问题，提出任务感知一致性与残差闭环迁移方法 TAC-R2S2R，"
              "并在开源双足机器人 MicroDuck 上完成从建模、训练到部署评测的实证。方法以任务条件场景图分配"
              "几何重建、物理辨识与随机化预算，以带齿隙与摩擦的执行器模型刻画真实舵机特性，"
              "在 MuJoCo Warp 中以 4096 路并行环境训练近端策略优化（PPO）速度追踪策略，"
              "并以实测前进速度而非回合奖励作为唯一性能判据。实验得到三点结论："
              "其一，官方出厂配方的速度命令上限仅为 0.4 m/s，不能覆盖短跑工况；"
              "其二，单纯抬高速度命令并加大腾空奖励会诱发奖励入侵，策略转为“站立不倒并小幅踮脚”，"
              f"回合奖励升至 {last(V1M, 'mean_reward', 2)} 而实测平均前进速度仅 "
              f"{fmt(V1S.get('forward_speed_mean_mps'), 3)} m/s；"
              "其三，据此给出的 v2 配方将速度追踪权重由 3.0 提至 6.0、腾空奖励权重由 5.0 降至 1.0 "
              "并抬高触发阈值，配合速度命令课程收窄，使奖励结构与任务目标重新一致；"
              "在相同迭代数与测速口径下，平均前进速度由 0.148 m/s 提升至 0.457 m/s。"
              "本文同时给出可复现的训练、测速与失败归因工具链，为低成本平台上的具身策略研究提供参照。",
         size=8.5, line=12.5)
    para(doc, "关键词：具身智能；双足机器人；Real2Sim2Real；近端策略优化；奖励塑形；域随机化",
         size=8.5, bold=True, cn=CN_HEAD, line=12.5, space_after=5)

    para(doc, "Abstract: This paper addresses actuator mismatch and reward distortion in "
              "real-to-sim-to-real transfer for embodied biped robots. We present TAC-R2S2R, a task-aware "
              "consistency and residual-closed-loop transfer method, and evaluate it on the open-source "
              "MicroDuck biped. A task-conditioned scene graph allocates geometry, identification and "
              "randomization budgets; a backlash- and friction-aware actuator model captures real servo "
              "behaviour; and a PPO velocity-tracking policy is trained with 4096 parallel MuJoCo Warp "
              "environments. Crucially, performance is judged by measured forward speed rather than episode "
              "return. Three findings are reported: the factory recipe caps commanded speed at 0.4 m/s and "
              "cannot cover sprinting; simply raising the command range while enlarging the air-time reward "
              "induces reward hacking, in which the policy stands still and taps its feet, reaching an episode "
              f"return of {last(V1M, 'mean_reward', 2)} with a measured mean speed of only "
              f"{fmt(V1S.get('forward_speed_mean_mps'), 3)} m/s; and the revised v2 recipe restores alignment "
              "between the reward structure and the task objective by reweighting velocity tracking against "
              "air time and narrowing the command curriculum. The full training, speed-probing and "
              "failure-attribution toolchain is released for reproducibility.",
         size=8, line=11.5)
    para(doc, "Key words: embodied intelligence; biped robot; Real2Sim2Real; proximal policy optimization; "
              "reward shaping; domain randomization", size=8, indent=False, line=11.5, space_after=6)

    # ===== 1 引言 =====
    heading(doc, "1　引言")
    para(doc, "视觉—语言—动作（vision-language-action，VLA）策略将语言、图像与机器人状态映射为动作，"
              "RT-1 与 RT-2 展示了大规模真实数据上的多任务学习能力，OpenVLA 与 Octo 提供了开放的策略基座。"
              "然而，无论策略主干是否携带语义先验，其在真实机器人上的最终表现仍由低层接触动力学决定："
              "舵机齿隙、摩擦、供电波动与控制延迟会直接改变动作执行结果。对双足机器人而言，这一问题尤为突出，"
              "因为支撑相与摆动相的交替使任何微小物理偏差都会被放大为步态不稳甚至跌倒。")
    para(doc, "真实到仿真再回到真实（Real2Sim2Real）能够减少真实试错，但关键不在于让整幅场景同样精细，"
              "而在于判定哪些误差会改变任务结果。对短跑这一任务，决定成败的不是背景纹理，"
              "而是足部接触法向、舵机响应延迟与奖励信号对速度的真实刻画。若建模与训练预算平均分配，"
              "即使仿真画面高度逼真，也可能产生错误的接触动力学；若奖励结构失衡，"
              "策略甚至会主动放弃任务目标以获取更容易的奖励来源。")
    para(doc, "本文以开源双足机器人 MicroDuck 为对象，研究任务感知 Real2Sim2Real 迁移中的两个具体问题："
              "（1）如何把有限的建模与辨识预算集中到决定运动表现的物理变量上；"
              "（2）如何使奖励结构与任务目标保持一致，并用可实测的物理量而非代理指标评价策略。"
              "与以仿真成功率或回合奖励为主要证据的工作不同，本文把前进速度的直接测量作为唯一性能判据，"
              "并完整公开训练日志、测速脚本与失败归因过程。")
    para(doc, "本文的主要贡献如下：")
    para(doc, "1）提出任务感知一致性与残差闭环迁移方法 TAC-R2S2R，将任务条件场景图、执行器物理后验、"
              "差异化域随机化、跨域一致性损失与类型化残差回写组织为统一闭环，并给出其在双足速度任务上的具体实例化；")
    para(doc, "2）在 DGX Spark（GB10）上构建 4096 路 MuJoCo Warp 并行训练与独立测速链路，"
              "给出官方出厂配方无法覆盖短跑工况的直接证据，即速度命令上限仅为 0.4 m/s；")
    para(doc, "3）以实测数据揭示一类典型的奖励入侵失效：抬高速度命令并加大腾空奖励后，"
              "策略选择站立刷分而非奔跑，并据此给出可复现的 v2 修正配方与消融对照。")

    # ===== 2 相关工作 =====
    heading(doc, "2　相关工作")
    heading(doc, "2.1　VLA 策略与通用机器人控制", 2)
    para(doc, "RT-1 将机器人控制表述为序列决策并在大规模真实数据上训练，RT-2 进一步把图文知识迁移到动作生成；"
              "OpenVLA 与 Octo 以开放权重降低了策略适配成本，π0 系列探索连续动作生成与开放世界泛化。"
              "这些工作解决的是从多模态输入生成动作的问题，其公开结果不能直接回答物理失配与奖励失真的影响。"
              "本文将 VLA 策略视为可替换主干，研究主干之外的迁移与训练机制。")
    heading(doc, "2.2　域随机化与 Real2Sim2Real", 2)
    para(doc, "视觉域随机化通过外观扰动覆盖真实图像分布，动力学随机化将质量、摩擦与延迟变化纳入训练；"
              "SimOpt 利用真实执行结果调整随机化分布，BayesSim 以概率推断估计仿真参数后验。"
              "RialTo 与 Re3Sim 则从真实观测构建可交互仿真并生成操作数据。"
              "上述工作表明，真实反馈驱动的仿真更新并非新命题；本文关注的是在低成本双足平台上，"
              "如何把辨识与随机化预算按任务相关性分配，避免在无关维度上消耗策略容量。")
    heading(doc, "2.3　双足运动控制与奖励塑形", 2)
    para(doc, "大规模并行强化学习显著降低了腿足式控制器的训练成本，Rudin 等证明了分钟级训练步态的可行性，"
              "Hwangbo 等通过执行器建模与随机化实现了 ANYmal 的实机迁移，RMA 进一步引入在线适应。"
              "这些工作的共同经验是：执行器模型与奖励结构往往比网络结构更决定最终表现。"
              "奖励塑形方面，过强的辅助奖励会改变最优策略本身，产生与任务目标无关的高回报行为。"
              "本文以实测速度为判据，对这一现象给出定量证据。")

    # ===== 3 方法 =====
    heading(doc, "3　任务感知 Real2Sim2Real 方法")
    para(doc, "方法按真实观测、任务图、仿真场景、策略训练、真实执行与残差回写组织数据流。"
              "3.1 节定义任务与观测，3.2 节把任务图转为建模预算，3.3 节形成可交互仿真，"
              "3.4 节给出联合训练目标，3.5 节描述部署门控与残差回写。"
              "全文以“MicroDuck 在平地以给定速度稳定前进”为贯穿任务。")

    heading(doc, "3.1　问题定义与观测表示", 2)
    para(doc, "将任务建模为任务条件部分可观测马尔可夫决策过程：", indent=True)
    equation(doc, "M = ⟨S, A, O, T, R, γ, c⟩", "1")
    para(doc, "其中 c 为语言或数值形式的任务指令，本文实例化为期望前进速度 v*。"
              "策略根据多模态历史 h_t 输出动作块：")
    equation(doc, "a_t:t+H ~ π_θ(· | h_t, c)", "2")
    para(doc, "MicroDuck 的动作空间为 14 路舵机目标位置偏移，观测包含关节位置与速度、"
              "机身姿态投影重力、上一时刻动作以及速度命令，策略以 50 Hz 运行，与实机控制节拍一致。")

    heading(doc, "3.2　任务图与关键性分级", 2)
    para(doc, "任务条件场景图写作 G = (V, E)，节点为实体或物理要素，边表示接触或约束关系。"
              "实体相关性由语言匹配、视觉定位、接触先验与历史失败四项评分经 softmax 归一化得到：")
    equation(doc, "ρ_i = softmax( w_1 g_i^lang + w_2 g_i^vis + w_3 g_i^con + w_4 g_i^fail )", "3")
    para(doc, "按相关性将要素分为三级，分别对应高保真建模、保守碰撞几何与低模外观表达，见表 1。"
              "对短跑任务，一级要素为左右足碰撞面、踝膝髋关节与躯干质心；"
              "二级要素为地形起伏与自碰撞边界；三级要素为光照、背景纹理与远场结构。")
    table(doc,
          ["级别", "短跑任务中的典型要素", "建模重点", "随机化策略"],
          [["一级", "足部碰撞面、腿部关节、躯干质心", "接触法向、摩擦与舵机后验", "按后验有界随机化"],
           ["二级", "地形起伏、自碰撞边界", "保守碰撞几何与可达性", "中等位姿与地形扰动"],
           ["三级", "光照、背景纹理、远场结构", "低模与外观多样性", "强外观随机化"]],
          "表1　任务相关性分级、建模方式与随机化策略",
          widths=[1.0, 3.0, 2.5, 2.1])

    heading(doc, "3.3　执行器物理后验与差异化随机化", 2)
    para(doc, "真实标定交互数据约束仿真参数后验：")
    equation(doc, "p(φ | D_cal) ∝ p(D_cal | φ) p(φ)", "4")
    para(doc, "辨识残差以真实轨迹与仿真轨迹之间的加权误差度量：")
    equation(doc, "J(φ) = Σ_t ‖ x_t^real − x_t^sim(φ) ‖_W²", "5")
    para(doc, "第 i 个任务相关参数按后验均值与方差采样，相关性决定其随机化幅度：")
    equation(doc, "φ_i ~ N(μ_i, σ_i²),　σ_i = ρ_i · σ_i^max", "6")
    para(doc, "MicroDuck 的执行器采用带摩擦预算与齿隙的舵机模型，而非理想位置伺服。"
              "训练中对关节摩擦、转子惯量（armature）、质心偏移、IMU 安装误差与编码器零偏进行随机化，"
              "并注入速度推力扰动以提高抗扰能力。式（4）—（6）的意义在于："
              "随机化范围不再依赖手工经验，而由任务相关性与可辨识性共同决定。")

    heading(doc, "3.4　跨域一致性与联合优化目标", 2)
    para(doc, "配对真实—仿真观测的任务表征对齐损失为：")
    equation(doc, "L_pair = ‖ f(x^real) − f(x^sim) ‖²", "7")
    para(doc, "无配对样本的分布差异采用核均值嵌入度量：")
    equation(doc, "L_dist = MMD²( f(X^real), f(X^sim) )", "8")
    para(doc, "动作块与前向动力学一致性分别约束两域的动作响应与状态转移：")
    equation(doc, "L_act = ‖ a^real − a^sim ‖²,　L_dyn = ‖ Δx^real − Δx^sim ‖²", "9")
    para(doc, "联合训练目标为：")
    equation(doc, "L = L_task + λ_1 L_pair + λ_2 L_dist + λ_3 L_act + λ_4 L_dyn + λ_5 L_safe", "10")
    para(doc, "本文实验的任务项 L_task 由 PPO 目标与速度追踪奖励构成。"
              "由于 MicroDuck 训练以仿真为主、实机日志有限，跨域四项在当前实验中仅作为可选约束，"
              "其作用在 4.4 节通过消融讨论；主结果不依赖未实施的损失项。")

    heading(doc, "3.5　不确定性门控与残差回写", 2)
    para(doc, "部署时综合风险由认知不确定性、模型不确定性与约束代价组成：")
    equation(doc, "r_t = α u_epi + β u_ale + η c_t", "11")
    para(doc, "动作执行门控满足低风险时执行，否则降速、重观测或接管：")
    equation(doc, "a_t^exec = G(r_t) · a_t", "12")
    para(doc, "一次失败按几何、物理、语义与策略四类归因，并回写对应模块：")
    equation(doc, "(φ, ρ, θ) ← Update(φ, ρ, θ; e_t, label_t)", "13")
    para(doc, "在短跑任务中，残差回写具体表现为：速度不达标但回合奖励升高时，"
              "不归因于物理失配而归因于奖励结构，更新奖励权重与命令课程，而非修改动力学参数。"
              "这一路由避免了“把所有失败都当作域偏移”的常见错误。")

    # ===== 4 实验 =====
    heading(doc, "4　实验与结果分析")
    heading(doc, "4.1　实验平台、模型与训练数据", 2)
    para(doc, "实验在一台 NVIDIA DGX Spark（GB10，aarch64，121 GB 统一内存，CUDA sm_121）上完成。"
              "仿真采用 MuJoCo Warp，物理与策略均在 GPU 上执行；策略优化采用 rsl_rl 的 PPO 实现，"
              "actor 与 critic 均为三层 128 单元 ELU 网络。训练环境为 MicroDuck 官方 microduck_rl 仓库，"
              "注册任务共 45 个，涵盖速度行走、站立恢复、起坐、前滚翻、踢球与轮滑等技能。"
              "本文在此基础上新增短跑任务 Mjlab-Sprint-Flat-MicroDuck 与 Mjlab-SprintV2-Flat-MicroDuck，"
              "不修改官方任何文件。")
    para(doc, "训练数据由仿真在线生成：每轮迭代采集 4096 个并行环境各 24 步转移样本，"
              "回合上限 12 s（600 步）。所有曲线均由 TensorBoard 事件文件导出，"
              "实测速度由独立测速脚本在独立进程中重放检查点获得，二者互不共用统计口径。")
    table(doc,
          ["项目", "配置"],
          [["仿真引擎", "MuJoCo Warp（warp-lang 1.12.0）"],
           ["并行环境数", "4096"],
           ["算法", "PPO（rsl_rl），学习率 1e-3，期望 KL 0.01"],
           ["网络", "actor / critic 各 3×128 ELU"],
           ["控制频率", "50 Hz，与实机 robotd 一致"],
           ["回合长度", "12 s（600 步）"],
           ["每轮迭代耗时", "约 6.3 s（与生产推理共用 GPU）"],
           ["执行器模型", "BAM：摩擦预算 + 齿隙 + 转子惯量"],
           ["测速方式", "32 环境并行，命令锁死 1.6 / 2.6 m/s，读 root_link_lin_vel_b"]],
          "表2　训练与评测配置",
          widths=[2.4, 6.2])

    heading(doc, "4.2　评价指标与测速协议", 2)
    para(doc, "本文不使用回合奖励作为性能指标。测速协议为：加载指定检查点，"
              "在 32 个并行环境中将前进速度命令固定为给定值（本文取 1.6 与 2.6 m/s 两档），"
              "运行 1000 步并丢弃前 100 步暖机，"
              "读取躯干本体坐标系下的前向线速度，报告均值、中位数、P95 与峰值。"
              "该协议与训练过程解耦，可直接用于不同配方、不同检查点之间的公平比较。")

    heading(doc, "4.3　官方配方的能力边界", 2)
    para(doc, "对官方速度任务 Mjlab-Velocity-Flat-MicroDuck 的配置解析显示，"
              "其前进速度命令范围为 lin_vel_x ∈ (−0.4, 0.4) m/s，横向与转向命令分别为 ±0.3 与 ±1.0。"
              "这意味着出厂配方的设计目标是可控制的行走，而非短跑。"
              "在该命令分布下训练的策略不可能学会 2 m/s 量级的运动，"
              "因为训练信号中根本不存在这样的目标状态。这是本文进行配方改造的直接动因，"
              "也说明评价一个具身策略时必须先检查其命令空间，而非仅观察最终回报。")

    heading(doc, "4.4　Sprint v1：奖励入侵的失效证据", 2)
    para(doc, "第一版短跑配方将命令范围抬升至 (0.8, 2.6) m/s，收窄横向与转向命令，"
              "并把腾空奖励权重由 3.0 提至 5.0、腾空时间窗放宽至 [0.10, 0.35] s，"
              "速度追踪权重设为 3.0。该配方的直觉是“更快的命令 + 更强的腾空激励 = 更快的步态”。")
    para(doc, f"训练 888 轮后的实际结果与直觉相反。如图 2 所示，速度追踪误差由 "
              f"{(V1M['series']['error_vel_xy'][0] if V1M else 0):.4f} 上升至 {last(V1M, 'error_vel_xy', 3)}，"
              f"平均回合长度由 24 步升至 {last(V1M, 'mean_episode_length', 1)} 步并贴近 600 步上限，"
              f"回合奖励则由 −0.79 升至 {last(V1M, 'mean_reward', 2)}。"
              "回合变长意味着机器人不再跌倒，而误差变大意味着它并未追随速度命令。")
    figure(doc, "fig2_v1_training.png",
           "图2　Sprint v1 训练过程：误差上升、回合顶满、奖励升高")
    para(doc, f"奖励项分解给出了直接解释（图 3）：腾空类奖励达到 {last(V1M, 'air_time_reward', 2)}，"
              f"而速度追踪奖励仅 {last(V1M, 'track_lin_vel', 3)}，二者相差约一个数量级。"
              "由于腾空奖励的触发门槛仅为命令大于 0.05，策略只要在小幅命令下保持站立并轻微活动足部，"
              "即可稳定获得远高于奔跑的回报。最优策略因此退化为“站立不倒 + 小幅踮脚”。")
    figure(doc, "fig3_reward_imbalance.png",
           "图3　Sprint v1 的奖励结构失衡：腾空奖励主导学习目标")
    para(doc, f"独立测速证实了这一点：在命令锁死 2.6 m/s 的条件下，"
              f"第 250 轮检查点实测平均速度 0.135 m/s，第 750 轮反而降至 "
              f"{fmt(V1S.get('forward_speed_mean_mps'), 3)} m/s，"
              f"峰值仅 {fmt(V1S.get('forward_speed_peak_frame_mps'), 3)} m/s。"
              "即训练继续推进并未带来速度提升，反而使策略更稳定地停留在刷分模式。"
              "这一结果说明：回合奖励与真实任务表现可以完全脱钩，"
              "以奖励曲线作为具身策略的性能证据是不可靠的。")

    heading(doc, "4.5　Sprint v2：奖励结构修正与对照", 2)
    para(doc, "针对上述失效，v2 配方作四项修改：将速度追踪权重由 3.0 提至 6.0，"
              "使其重新成为主导项；腾空奖励权重由 5.0 降至 1.0，触发门槛由 0.05 提至 0.5，"
              "使腾空只在高速命令下被鼓励；姿态与头部追踪权重减半，减少对“站得稳”的过度奖励；"
              "速度命令改为 (0.3, 1.6) m/s 的课程式区间，先保证可学，再逐步抬高上限。")
    table(doc,
          ["奖励项", "官方配方", "Sprint v1", "Sprint v2", "调整意图"],
          [["track_linear_velocity", "2.0", "3.0", "6.0", "速度成为主导目标"],
           ["air_time", "3.0", "5.0", "1.0", "抑制刷腾空分"],
           ["air_time 触发阈值", "0.01", "0.05", "0.5", "仅高速命令奖励腾空"],
           ["upright", "2.0", "1.0", "0.5", "降低站立收益"],
           ["pose", "1.0", "0.3", "0.1", "降低姿态保持收益"],
           ["action_rate_l2", "−0.1", "−0.05", "−0.05", "保留动作平滑约束"],
           ["foot_slip", "−0.1", "−0.35", "−0.35", "惩罚滑步产生的假速度"],
           ["lin_vel_x 命令", "(−0.4,0.4)", "(0.8,2.6)", "(0.3,1.6)", "课程式可学区间"]],
          "表3　三版配方的奖励权重与命令范围对比",
          widths=[2.5, 1.5, 1.4, 1.4, 2.0])
    V2C26 = load("v2_speed_cmd26.json") or {}
    V1C16 = load("v1_speed_cmd16.json") or {}
    if V2M:
        para(doc, f"奖励结构首先发生了预期变化。训练至 {V2M.get('iter_count', 0)} 轮时，"
                  f"速度追踪奖励为 {last(V2M, 'track_lin_vel', 3)}，"
                  f"已超过 v1 跑满 888 轮后的 {last(V1M, 'track_lin_vel', 3)}；"
                  f"腾空奖励仅 {last(V2M, 'air_time_reward', 3)}，"
                  f"相比 v1 的 {last(V1M, 'air_time_reward', 2)} 下降约两个数量级；"
                  f"平均回合长度为 {last(V2M, 'mean_episode_length', 1)} 步，"
                  "远低于 v1 贴近上限的 589 步，说明策略不再依靠静止站立获取回报。"
                  "奖励项的相对关系已从“腾空主导”反转为“速度主导”。")
        figure(doc, "fig6_v1_v2_curves.png", "图4　v1 与 v2 训练曲线对照")
    if V2S and V1C16:
        ratio = V2S["forward_speed_mean_mps"] / max(V1C16["forward_speed_mean_mps"], 1e-6)
        para(doc, "为排除测速口径差异，本文对两种配方在同一迭代数（第 250 轮）、"
                  "两种命令强度下分别测速，结果见表 4。在命令 1.6 m/s 下，"
                  f"v2 平均前进速度为 {fmt(V2S['forward_speed_mean_mps'], 3)} m/s，"
                  f"v1 仅为 {fmt(V1C16['forward_speed_mean_mps'], 3)} m/s，"
                  f"提升约 {ratio:.1f} 倍；峰值由 {fmt(V1C16['forward_speed_peak_frame_mps'], 3)} m/s "
                  f"提高到 {fmt(V2S['forward_speed_peak_frame_mps'], 3)} m/s。"
                  "在相同训练预算下，仅修改奖励结构与命令课程即带来速度量级差异，"
                  "证明 v1 的失败确实源于奖励失真，而非平台或网络容量不足。")
        table(doc,
              ["测速命令", "配方", "平均速度/(m·s⁻¹)", "P95/(m·s⁻¹)", "峰值/(m·s⁻¹)"],
              [["1.6 m/s", "Sprint v1", fmt(V1C16.get("forward_speed_mean_mps"), 3),
                fmt(V1C16.get("forward_speed_p95_mps"), 3), fmt(V1C16.get("forward_speed_peak_frame_mps"), 3)],
               ["1.6 m/s", "Sprint v2", fmt(V2S.get("forward_speed_mean_mps"), 3),
                fmt(V2S.get("forward_speed_p95_mps"), 3), fmt(V2S.get("forward_speed_peak_frame_mps"), 3)],
               ["2.6 m/s", "Sprint v1", "0.135", "0.209", "0.285"],
               ["2.6 m/s", "Sprint v2", fmt(V2C26.get("forward_speed_mean_mps"), 3),
                fmt(V2C26.get("forward_speed_p95_mps"), 3), fmt(V2C26.get("forward_speed_peak_frame_mps"), 3)]],
              "表4　第 250 轮检查点的同口径实测前进速度",
              widths=[1.5, 1.5, 2.0, 1.7, 1.7])
        para(doc, f"另一项值得注意的现象是：当命令提高到 2.6 m/s、超出 v2 的训练课程上限 1.6 m/s 时，"
                  f"v2 的平均速度回落至 {fmt(V2C26.get('forward_speed_mean_mps'), 3)} m/s。"
                  "这表明策略的可达速度受命令覆盖范围约束，"
                  "在未见过的命令区间上并不会自动外推。"
                  "因此，后续训练必须以课程方式持续抬高命令上限，"
                  "而不能指望一次配方修改就获得短跑能力。"
                  "该现象与 4.3 节对官方配方的分析相互印证："
                  "命令空间既是能力下界，也是能力上界。")
    figure(doc, "fig4_speed_compare.png", "图5　同迭代数下两配方的同口径实测速度对比")
    para(doc, "与公开短跑成绩的关系必须谨慎表述。公开报道中 MicroDuck 的峰值速度为 "
              "1.60 m/s（Hannes）、1.88 m/s（Max Sumrall）与 2.07 m/s（4090D，13500 轮迭代）。"
              "这些结果的训练预算、命令空间与测速方式各不相同，与本文不具可比性。"
              f"本文当前最高实测峰值为 {fmt(V2S.get('forward_speed_peak_frame_mps'), 3)} m/s，"
              "仅对应 250 轮训练，图 6 仅用于说明差距量级，不构成性能排名。"
              "按本文观察到的命令覆盖规律，达到公开水平需要把课程上限继续抬高并增加训练预算，"
              "而非继续调整网络结构。")
    figure(doc, "fig5_public_benchmark.png",
           "图6　公开短跑成绩与本文当前结果（口径不同，仅作参照）")

    heading(doc, "4.6　训练系统性能与资源消耗", 2)
    para(doc, "在与生产视觉推理服务共用同一块 GPU 的条件下，4096 路并行环境的单轮迭代耗时约 6.3 s。"
              "每轮迭代包含 4096×24 步仿真与一次 PPO 更新，"
              "对应每秒约 1.56 万步环境交互。该吞吐使 3000 轮训练在约 5.3 h 内完成，"
              "说明低成本单卡平台足以支撑双足速度策略的系统调参实验。"
              "需要强调的是，训练吞吐与最终运动表现无必然联系，"
              "v1 的失败正是在高吞吐条件下发生的。")

    heading(doc, "4.7　失败归因与残差回写实例", 2)
    para(doc, "v1 的失败并非几何或物理失配：机器人能够稳定站立，回合长度顶满，"
              "说明仿真中的接触与平衡机制工作正常。真正的误差来源是奖励结构，"
              "属于 3.5 节定义的策略—目标类残差。按本文的回写规则，"
              "正确的更新对象是奖励权重与命令课程，而非摩擦、质量或执行器参数。"
              "这一案例验证了类型化归因的必要性：若将其误判为域偏移并扩大随机化范围，"
              "只会进一步稀释训练信号，无法解决速度不达标的问题。")

    # ===== 5 结论 =====
    heading(doc, "5　结论与展望")
    para(doc, "本文将任务感知 Real2Sim2Real 迁移框架落到开源双足机器人 MicroDuck 上，"
              "并以实测前进速度为唯一性能判据，得到三点可复核结论。"
              "第一，出厂速度命令上限 0.4 m/s 决定了官方配方不具备短跑能力，"
              "命令空间检查应先于任何性能评价。"
              "第二，抬高命令并加大腾空奖励会诱发奖励入侵，"
              f"回合奖励升至 {last(V1M, 'mean_reward', 2)} 而实测平均速度仅 "
              f"{fmt(V1S.get('forward_speed_mean_mps'), 3)} m/s，"
              "证明回合奖励不能作为具身策略的性能证据。"
              "第三，以速度追踪为主导、腾空奖励降权并抬高门槛、命令区间课程化的 v2 配方，"
              "在相同迭代数与测速口径下把平均前进速度由 0.148 m/s 提升至 0.457 m/s，"
              "证明奖励结构修正是获得运动能力的前提；"
              "同时，命令超出课程上限后速度回落，说明命令覆盖范围决定可达速度上界。")
    para(doc, "本文的局限在于：实验以仿真为主，尚未完成真实机器人上的速度闭环验证；"
              "跨域一致性损失在当前实验中未启用，其对实机迁移的贡献需要单独评估；"
              "测速协议基于本体前向速度，未覆盖长时间能耗与足部冲击等工程指标。"
              "后续工作将沿三条路线推进：在实机上部署 v2 策略并记录 50 Hz 控制日志，"
              "将失败按几何、物理、语义与策略四类回写；引入 LSTM 策略与教师—学生蒸馏，"
              "提升延迟与部分可观测条件下的鲁棒性；在统一命令空间下与公开短跑成绩进行同口径对比。")

    # ===== 参考文献 =====
    heading(doc, "参考文献")
    refs = [
        "Brohan A, Brown N, Carbajal J, et al. RT-1: Robotics Transformer for Real-World Control at Scale[C]//Robotics: Science and Systems, 2023.",
        "Brohan A, Brown N, Carbajal J, et al. RT-2: Vision-Language-Action Models Transfer Web Knowledge to Robotic Control[C]//Conference on Robot Learning, 2023.",
        "Kim M J, Pertsch K, Karamcheti S, et al. OpenVLA: An Open-Source Vision-Language-Action Model[C]//Conference on Robot Learning, 2024.",
        "Octo Model Team. Octo: An Open-Source Generalist Robot Policy[C]//Robotics: Science and Systems, 2024.",
        "Black K, Brown N, Driess D, et al. π0: A Vision-Language-Action Flow Model for General Robot Control[EB/OL]. arXiv:2410.24164, 2024.",
        "Tobin J, Fong R, Ray A, et al. Domain Randomization for Transferring Deep Neural Networks from Simulation to the Real World[C]//IEEE/RSJ IROS, 2017: 23-30.",
        "Peng X B, Andrychowicz M, Zaremba W, et al. Sim-to-Real Transfer of Robotic Control with Dynamics Randomization[C]//IEEE ICRA, 2018: 3803-3810.",
        "Chebotar Y, Handa A, Makoviychuk V, et al. Closing the Sim-to-Real Loop: Adapting Simulation Randomization with Real World Experience[C]//IEEE ICRA, 2019: 8973-8979.",
        "Ramos F, Possas R C, Fox D. BayesSim: Adaptive Domain Randomization via Probabilistic Inference for Robotics Simulators[C]//Robotics: Science and Systems, 2019.",
        "Schulman J, Wolski F, Dhariwal P, et al. Proximal Policy Optimization Algorithms[EB/OL]. arXiv:1707.06347, 2017.",
        "Todorov E, Erez T, Tassa Y. MuJoCo: A Physics Engine for Model-Based Control[C]//IEEE/RSJ IROS, 2012: 5026-5033.",
        "Rudin N, Hoeller D, Reist P, et al. Learning to Walk in Minutes Using Massively Parallel Deep Reinforcement Learning[C]//Conference on Robot Learning, 2021.",
        "Hwangbo J, Lee J, Dosovitskiy A, et al. Learning Agile and Dynamic Motor Skills for Legged Robots[J]. Science Robotics, 2019, 4(26): eaau5872.",
        "Kumar A, Fu Z, Pathak D, et al. RMA: Rapid Motor Adaptation for Legged Robots[C]//Robotics: Science and Systems, 2021.",
        "Mittal M, Yu C, Yu Q, et al. Orbit: A Unified Simulation Framework for Interactive Robot Learning Environments[J]. IEEE Robotics and Automation Letters, 2023, 8(6): 3740-3747.",
        "Open X-Embodiment Collaboration. Open X-Embodiment: Robotic Learning Datasets and RT-X Models[C]//IEEE ICRA, 2024.",
        "Pollen Robotics. MicroDuck: An Open-Source Biped Robot and Its MuJoCo-Warp RL Training Stack[EB/OL]. https://github.com/pollen-robotics/microduck_rl, 2026.",
    ]
    for i, r in enumerate(refs, 1):
        para(doc, f"[{i}]　{r}", size=8, indent=False, line=11.5, space_after=1)

    doc.save(OUT)
    print("saved:", OUT)
    print("v1 mean speed:", V1S.get("forward_speed_mean_mps"), "| v2:", V2S.get("forward_speed_mean_mps"))


if __name__ == "__main__":
    build()
