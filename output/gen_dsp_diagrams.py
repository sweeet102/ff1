#!/usr/bin/env python3
"""用 matplotlib 生成 DSP 课设报告中的 4 张流程图，高 DPI 保证清晰度."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.lines as mlines
import numpy as np
import os, io

# ── 全局设置 ──
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Heiti TC', 'STHeiti', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

DPI = 150
OUT_DIR = '/Users/wenzhiyuan/Desktop/ff1/output/diagrams_mpl'

os.makedirs(OUT_DIR, exist_ok=True)

# ── 配色 ──
C = {
    'box_blue':    '#D6E8F7',
    'border_blue': '#3A7CC3',
    'box_orange':  '#FDE8D0',
    'border_orange':'#C38A3A',
    'box_green':   '#D8F0D8',
    'border_green':'#3A8C3A',
    'box_purple':  '#E8D8F0',
    'border_purple':'#7A3A9A',
    'text':        '#222222',
    'arrow':       '#555555',
    'loop':        '#7AA8CC',
    'bg':          '#FFFFFF',
}

def rounded_box(ax, x, y, w, h, color=C['box_blue'], edge=C['border_blue'],
                lw=2, radius=0.08):
    """绘制圆角矩形"""
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle=f"round,pad=0,rounding_size={radius}",
                         facecolor=color, edgecolor=edge, linewidth=lw,
                         zorder=2)
    ax.add_patch(box)

def add_text(ax, x, y, w, h, text, fontsize=10, color=C['text'], bold=False):
    """在矩形框内居中写文字"""
    weight = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center',
            fontsize=fontsize, color=color, weight=weight, zorder=3,
            linespacing=1.4)

def arrow(ax, x0, y0, x1, y1, color=C['arrow'], lw=2.5, style='->,head_length=5,head_width=3'):
    """绘制箭头"""
    ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw,
                               connectionstyle='arc3,rad=0'),
                zorder=1)

def path_arrow(ax, x0, y0, x1, y1, mid_x, color=C['arrow'], lw=2):
    """折线箭头（用于循环返回）"""
    ax.plot([x0, mid_x, mid_x, x1], [y0, y0, y1, y1],
            color=color, lw=lw, zorder=1, clip_on=False)
    # 终点小三角
    ax.plot(x1, y1, marker='v', color=color, markersize=8, zorder=4, clip_on=False)

def save_fig(fig, name, dpi=DPI):
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=dpi, bbox_inches='tight', pad_inches=0.3,
                facecolor='white', edgecolor='none')
    plt.close(fig)
    # 返回字节流供 DOCX 嵌入
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', pad_inches=0.3,
                facecolor='white', edgecolor='none')
    buf.seek(0)
    print(f'  {name} saved ({os.path.getsize(path)} bytes)')
    return buf

# ═══════════════════════════════════════════
# 图 2-1：系统总体结构框图
# ═══════════════════════════════════════════

def fig2_1_system():
    fig, ax = plt.subplots(figsize=(10, 2.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    box_w, box_h = 0.18, 0.55
    gap = 0.06
    n = 4
    total_w = n * box_w + (n - 1) * gap
    start_x = (1 - total_w) / 2
    cy = 0.22

    blocks = [
        ('模拟信号\n(输入)', C['box_blue'], C['border_blue']),
        ('AD 模数转换\n(ICETEK5509)', C['box_orange'], C['border_orange']),
        ('FFT 频谱分析\n(C 语言实现)', C['box_blue'], C['border_blue']),
        ('频谱显示\n(CCS Graph)', C['box_green'], C['border_green']),
    ]

    for i, (text, fill, edge) in enumerate(blocks):
        x = start_x + i * (box_w + gap)
        rounded_box(ax, x, cy, box_w, box_h, fill, edge, radius=0.04)
        add_text(ax, x, cy, box_w, box_h, text, fontsize=10)
        if i < n - 1:
            ax0 = x + box_w
            ay0 = cy + box_h / 2
            ax1 = x + box_w + gap
            arrow(ax, ax0, ay0, ax1, ay0)

    # 图标题
    ax.text(0.5, 0.02, '图 2-1  系统总体结构框图', transform=ax.transAxes,
            ha='center', fontsize=10, color='#666')

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=DPI, bbox_inches='tight', pad_inches=0.3,
                facecolor='white', edgecolor='none')
    buf.seek(0)
    fig.savefig(os.path.join(OUT_DIR, 'fig2-1_system.png'), dpi=DPI, bbox_inches='tight',
                pad_inches=0.3, facecolor='white', edgecolor='none')
    plt.close(fig)
    print('  fig2-1_system.png saved')
    return buf

# ═══════════════════════════════════════════
# 图 3-1：AD 模块设计流程
# ═══════════════════════════════════════════

def fig3_1_ad():
    fig, ax = plt.subplots(figsize=(9.6, 2.0))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    box_w, box_h = 0.18, 0.55
    gap = 0.05
    n = 4
    total_w = n * box_w + (n - 1) * gap
    start_x = (1 - total_w) / 2
    cy = 0.22

    blocks = [
        ('建立 CCS\n工程', C['box_blue'], C['border_blue']),
        ('导入 AD\n示例工程', C['box_blue'], C['border_blue']),
        ('编译下载\n运行验证', C['box_orange'], C['border_orange']),
        ('FileOut\n保存数据', C['box_green'], C['border_green']),
    ]

    for i, (text, fill, edge) in enumerate(blocks):
        x = start_x + i * (box_w + gap)
        rounded_box(ax, x, cy, box_w, box_h, fill, edge, radius=0.04)
        add_text(ax, x, cy, box_w, box_h, text, fontsize=10)
        if i < n - 1:
            ax0 = x + box_w
            ay0 = cy + box_h / 2
            ax1 = x + box_w + gap
            arrow(ax, ax0, ay0, ax1, ay0)

    ax.text(0.5, 0.02, '图 3-1  AD 模块设计流程', transform=ax.transAxes,
            ha='center', fontsize=10, color='#666')

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=DPI, bbox_inches='tight', pad_inches=0.3,
                facecolor='white', edgecolor='none')
    buf.seek(0)
    fig.savefig(os.path.join(OUT_DIR, 'fig3-1_ad.png'), dpi=DPI, bbox_inches='tight',
                pad_inches=0.3, facecolor='white', edgecolor='none')
    plt.close(fig)
    print('  fig3-1_ad.png saved')
    return buf

# ═══════════════════════════════════════════
# 图 3-2：FFT 软件设计流程
# ═══════════════════════════════════════════

def fig3_2_fft():
    fig, ax = plt.subplots(figsize=(10.8, 2.0))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    box_w, box_h = 0.15, 0.55
    gap = 0.04
    n = 5
    total_w = n * box_w + (n - 1) * gap
    start_x = (1 - total_w) / 2
    cy = 0.22

    blocks = [
        ('设计测试\n信号', C['box_blue'], C['border_blue']),
        ('预计算\n旋转因子', C['box_blue'], C['border_blue']),
        ('位反转\n排序', C['box_orange'], C['border_orange']),
        ('蝶形运算\n(log2N 级)', C['box_orange'], C['border_orange']),
        ('CCS Graph\n显示频谱', C['box_green'], C['border_green']),
    ]

    for i, (text, fill, edge) in enumerate(blocks):
        x = start_x + i * (box_w + gap)
        rounded_box(ax, x, cy, box_w, box_h, fill, edge, radius=0.04)
        add_text(ax, x, cy, box_w, box_h, text, fontsize=9.5)
        if i < n - 1:
            ax0 = x + box_w
            ay0 = cy + box_h / 2
            ax1 = x + box_w + gap
            arrow(ax, ax0, ay0, ax1, ay0)

    ax.text(0.5, 0.02, '图 3-2  FFT 软件设计流程', transform=ax.transAxes,
            ha='center', fontsize=10, color='#666')

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=DPI, bbox_inches='tight', pad_inches=0.3,
                facecolor='white', edgecolor='none')
    buf.seek(0)
    fig.savefig(os.path.join(OUT_DIR, 'fig3-2_fft.png'), dpi=DPI, bbox_inches='tight',
                pad_inches=0.3, facecolor='white', edgecolor='none')
    plt.close(fig)
    print('  fig3-2_fft.png saved')
    return buf

# ═══════════════════════════════════════════
# 图 3-3：系统主程序流程（结构化循环流程图）
# ═══════════════════════════════════════════

def fig3_3_main():
    fig, ax = plt.subplots(figsize=(7.0, 8.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 22)
    ax.axis('off')

    # ── 坐标系统（绝对坐标，便于调整）──
    mid = 5.0
    box_w = 7.0
    box_h = 1.0
    small_w = 6.0

    # ── 绘制函数 ──
    def box(x, y, w, h, text, fill=C['box_blue'], edge=C['border_blue'], fontsize=10):
        rounded_box(ax, x, y, w, h, fill, edge, radius=0.15)
        add_text(ax, x, y, w, h, text, fontsize=fontsize)

    def v_arrow(x, y0, y1):
        arrow(ax, x, y0, x, y1)

    # ── 起始椭圆 ──
    start_y = 20.0
    ellipse = mpatches.FancyBboxPatch((mid - 0.8, start_y - 0.5), 1.6, 1.0,
                                       boxstyle='round,pad=0.1,rounding_size=0.5',
                                       facecolor='#E0EBF5', edgecolor=C['border_blue'],
                                       linewidth=2, zorder=2)
    ax.add_patch(ellipse)
    ax.text(mid, start_y, '开  始', ha='center', va='center', fontsize=11,
            zorder=3)

    v_arrow(mid, start_y - 0.5, start_y - 1.5)

    # ── 系统初始化 ──
    init_y = start_y - 2.5
    box(mid - box_w/2, init_y, box_w, box_h + 0.2,
        '系统初始化\n（PLL · McBSP · ADC · 中断向量表）',
        fill=C['box_orange'], edge=C['border_orange'], fontsize=10)

    v_arrow(mid, init_y, init_y - 1.2)

    # ── while(1) 循环框 ──
    loop_top = init_y - 2.2
    loop_bottom = 3.0
    loop_h = loop_top - loop_bottom
    loop_x = 1.0
    loop_w = 8.0

    loop_rect = mpatches.FancyBboxPatch((loop_x, loop_bottom), loop_w, loop_h,
                                         boxstyle='round,pad=0,rounding_size=0.3',
                                         facecolor='none', edgecolor=C['loop'],
                                         linewidth=2, linestyle='--', zorder=0)
    ax.add_patch(loop_rect)
    ax.text(loop_x + 0.2, loop_top + 0.25, 'while (1)', fontsize=9,
            color=C['loop'], style='italic', zorder=3)

    # ── 循环体内三个步骤 ──
    cy = loop_top - 0.8
    step_h = 0.9
    step_gap = 0.6
    sx = mid - small_w / 2

    steps = [
        ('AD_Collect(buffer)    采集 N 点数据', C['box_blue'], C['border_blue']),
        ('FFT(buffer, N)        执行 N 点 FFT', C['box_blue'], C['border_blue']),
        ('DisplaySpectrum()     更新频谱显示', C['box_green'], C['border_green']),
    ]

    for i, (text, fill, edge) in enumerate(steps):
        yy = cy - step_h
        box(sx, yy, small_w, step_h, text, fill=fill, edge=edge, fontsize=9.5)
        if i < len(steps) - 1:
            v_arrow(mid, yy, yy - step_gap)
            cy = yy - step_gap
        last_y = yy
        cy = yy - step_gap

    # ── 循环返回箭头（右侧）──
    return_x = loop_x + loop_w + 0.8
    return_bottom = last_y
    return_top = loop_top - 0.2

    # 从最后一步底部 → 右侧 → 上升到循环顶部 → 左侧回到循环体内
    ax.plot([mid, return_x], [return_bottom, return_bottom], color=C['arrow'], lw=2, zorder=1)
    ax.plot([return_x, return_x], [return_bottom, return_top], color=C['arrow'], lw=2, zorder=1)
    ax.plot([return_x, mid], [return_top, return_top], color=C['arrow'], lw=2, zorder=1)
    # 向下箭头
    arrow(ax, mid, return_top, mid, return_top - 0.6)

    # ── 图标题 ──
    ax.text(5, 0.3, '图 3-3  系统主程序流程', ha='center', fontsize=10, color='#666')

    fig.tight_layout(pad=0.5)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=DPI, bbox_inches='tight', pad_inches=0.3,
                facecolor='white', edgecolor='none')
    buf.seek(0)
    fig.savefig(os.path.join(OUT_DIR, 'fig3-3_main.png'), dpi=DPI, bbox_inches='tight',
                pad_inches=0.3, facecolor='white', edgecolor='none')
    plt.close(fig)
    print('  fig3-3_main.png saved')
    return buf

# ═══════════════════════════════════════════
# 全部生成
# ═══════════════════════════════════════════

if __name__ == '__main__':
    print('Generating diagrams with matplotlib...')
    fig2_1_system()
    fig3_1_ad()
    fig3_2_fft()
    fig3_3_main()
    print(f'Done. Output in {OUT_DIR}')
