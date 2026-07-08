#!/usr/bin/env python3
"""Generate 4 Excalidraw diagrams for DSP experiment report."""
import json, uuid, os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

def new_id():
    return uuid.uuid4().hex[:20]

def rect(x, y, w, h, text="", bg="#a5d8ff", stroke="#1971c2", font_size=16):
    """Create a rectangle element."""
    eid = new_id()
    el = {
        "id": eid, "type": "rectangle", "x": x, "y": y, "width": w, "height": h,
        "strokeColor": stroke, "backgroundColor": bg, "fillStyle": "solid",
        "strokeWidth": 2, "roughness": 1, "opacity": 100,
        "roundness": {"type": 3}, "angle": 0, "groupIds": [], "frameId": None,
        "boundElements": [{"id": new_id(), "type": "text"}],
        "isDeleted": False, "locked": False, "version": 1
    }
    if text:
        el["boundElements"] = [{"id": eid + "t", "type": "text"}]
    return el

def text_box(x, y, w, h, text, font_size=16, text_align="center", vertical_align="middle"):
    """Create a text element bound to a container at the given position."""
    tid = new_id()
    return {
        "id": tid, "type": "text", "x": x, "y": y, "width": w, "height": max(h, font_size + 8),
        "strokeColor": "#1e1e1e", "backgroundColor": "transparent", "fillStyle": "solid",
        "strokeWidth": 1, "roughness": 1, "opacity": 100,
        "angle": 0, "groupIds": [], "frameId": None,
        "containerId": None, "isDeleted": False, "locked": False, "version": 1,
        "text": text, "fontSize": font_size, "fontFamily": 5,
        "textAlign": text_align, "verticalAlign": vertical_align,
        "autoResize": True,
        "lineHeight": 1.25
    }

def standalone_text(x, y, text, font_size=20, text_align="center"):
    """Create a standalone text element (for titles)."""
    tid = new_id()
    return {
        "id": tid, "type": "text", "x": x, "y": y, "width": len(text) * font_size * 0.7, "height": font_size + 8,
        "strokeColor": "#1e1e1e", "backgroundColor": "transparent", "fillStyle": "solid",
        "strokeWidth": 1, "roughness": 1, "opacity": 100,
        "angle": 0, "groupIds": [], "frameId": None,
        "containerId": None, "isDeleted": False, "locked": False, "version": 1,
        "text": text, "fontSize": font_size, "fontFamily": 5,
        "textAlign": text_align, "verticalAlign": "top",
        "autoResize": True, "lineHeight": 1.25
    }

def arrow(x1, y1, x2, y2, label="", stroke="#1e1e1e"):
    """Create an arrow element."""
    aid = new_id()
    el = {
        "id": aid, "type": "arrow", "x": x1, "y": y1,
        "width": x2 - x1, "height": y2 - y1,
        "strokeColor": stroke, "backgroundColor": "transparent", "fillStyle": "solid",
        "strokeWidth": 2, "roughness": 1, "opacity": 100,
        "roundness": {"type": 2}, "angle": 0, "groupIds": [], "frameId": None,
        "points": [[0, 0], [x2 - x1, y2 - y1]],
        "isDeleted": False, "locked": False, "version": 1
    }
    if label:
        el["boundElements"] = [{"id": aid + "t", "type": "text"}]
    return el

def arrow_label(x, y, text, font_size=14):
    return standalone_text(x, y, text, font_size, "center")

def make_excalidraw_file(elements, filename):
    data = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {"viewBackgroundColor": "#ffffff", "gridSize": 20},
        "files": {}
    }
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved: {path} ({len(elements)} elements)")


# ============================================================
# 图1 - 系统总体结构框图 (Architecture Diagram)
# ============================================================
def gen_diagram1():
    elements = []

    # Title
    elements.append(standalone_text(50, 10, "图1  系统总体结构框图", 24))

    # Three modules, horizontal layout
    box_w, box_h = 180, 90
    y_pos = 80
    gap = 60

    # Module 1: AD模数转换
    x1 = 60
    elements.append(rect(x1, y_pos, box_w, box_h, "", "#a5d8ff", "#1971c2"))
    elements.append(text_box(x1, y_pos + 10, box_w, 20, "AD模数转换", 16))
    elements.append(text_box(x1, y_pos + 35, box_w, 18, "ICETEK5509实验箱", 13))
    elements.append(text_box(x1, y_pos + 55, box_w, 18, "TLV320AIC23", 13))

    # Module 2: DSP CPU
    x2 = x1 + box_w + gap
    elements.append(rect(x2, y_pos, box_w, box_h, "", "#b2f2bb", "#2f9e44"))
    elements.append(text_box(x2, y_pos + 10, box_w, 20, "DSP CPU", 16))
    elements.append(text_box(x2, y_pos + 35, box_w, 18, "FFT频谱分析", 13))
    elements.append(text_box(x2, y_pos + 55, box_w, 18, "TMS320VC5509", 13))

    # Module 3: CCS Graph
    x3 = x2 + box_w + gap
    elements.append(rect(x3, y_pos, box_w, box_h, "", "#ffd43b", "#e8590c"))
    elements.append(text_box(x3, y_pos + 10, box_w, 20, "CCS Graph", 16))
    elements.append(text_box(x3, y_pos + 35, box_w, 18, "图形显示工具", 13))
    elements.append(text_box(x3, y_pos + 55, box_w, 18, "频谱结果输出", 13))

    # Arrows between modules
    ax1_end = x2
    elements.append(arrow(x1 + box_w, y_pos + box_h//2, x2, y_pos + box_h//2))
    elements.append(arrow_label(x1 + box_w + 5, y_pos + box_h//2 - 20, "数字序列", 13))

    elements.append(arrow(x2 + box_w, y_pos + box_h//2, x3, y_pos + box_h//2))
    elements.append(arrow_label(x2 + box_w + 5, y_pos + box_h//2 - 20, "频谱结果", 13))

    # Input label (left)
    elements.append(standalone_text(x1 - 10, y_pos + box_h//2 - 10, "模拟输入\n信号", 13, "right"))
    elements.append(arrow(x1 - 40, y_pos + box_h//2, x1, y_pos + box_h//2))

    make_excalidraw_file(elements, "fig1_system_architecture.excalidraw")


# ============================================================
# 图2 - AD模块设计流程 (Flowchart)
# ============================================================
def gen_diagram2():
    elements = []

    elements.append(standalone_text(50, 10, "图2  AD模块设计流程", 24))

    # Start ellipse
    start_x, start_y = 200, 70
    elements.append({
        "id": new_id(), "type": "ellipse", "x": start_x, "y": start_y, "width": 100, "height": 40,
        "strokeColor": "#1971c2", "backgroundColor": "#a5d8ff", "fillStyle": "solid",
        "strokeWidth": 2, "roughness": 1, "opacity": 100,
        "roundness": {"type": 2}, "angle": 0, "groupIds": [], "frameId": None,
        "isDeleted": False, "locked": False, "version": 1
    })
    elements.append(text_box(start_x, start_y + 8, 100, 24, "启动CCS", 16))

    # Steps as rectangles, vertical flow
    steps = [
        "配置仿真器\n建立硬件连接",
        "导入示例\nAD工程",
        "阅读源码\n添加中文注释",
        "编译工程\n下载到实验箱",
        "运行程序",
        "Watch窗口\n观察实时数据",
        "FileIO配置参数\n保存.dat文件",
    ]

    box_w, box_h = 180, 50
    x_center = start_x + 50 - box_w // 2
    y = start_y + 55

    prev_y_end = start_y + 40
    for i, step in enumerate(steps):
        elements.append(rect(x_center, y, box_w, box_h, "", "#a5d8ff", "#1971c2"))
        elements.append(text_box(x_center, y + 8, box_w, box_h - 10, step, 14))
        elements.append(arrow(x_center + box_w//2, prev_y_end, x_center + box_w//2, y))
        prev_y_end = y + box_h
        y += box_h + 20

    # End ellipse
    end_x = x_center
    end_y = y
    elements.append({
        "id": new_id(), "type": "ellipse", "x": end_x, "y": end_y, "width": 100, "height": 40,
        "strokeColor": "#2f9e44", "backgroundColor": "#b2f2bb", "fillStyle": "solid",
        "strokeWidth": 2, "roughness": 1, "opacity": 100,
        "roundness": {"type": 2}, "angle": 0, "groupIds": [], "frameId": None,
        "isDeleted": False, "locked": False, "version": 1
    })
    elements.append(text_box(end_x, end_y + 8, 100, 24, "结束", 16))
    elements.append(arrow(end_x + 50, prev_y_end, end_x + 50, end_y))

    make_excalidraw_file(elements, "fig2_ad_flowchart.excalidraw")


# ============================================================
# 图3 - FFT软件设计流程 (Flowchart)
# ============================================================
def gen_diagram3():
    elements = []

    elements.append(standalone_text(50, 10, "图3  FFT软件设计流程", 24))

    start_x, start_y = 220, 70
    elements.append({
        "id": new_id(), "type": "ellipse", "x": start_x, "y": start_y, "width": 80, "height": 36,
        "strokeColor": "#1971c2", "backgroundColor": "#a5d8ff", "fillStyle": "solid",
        "strokeWidth": 2, "roughness": 1, "opacity": 100,
        "roundness": {"type": 2}, "angle": 0, "groupIds": [], "frameId": None,
        "isDeleted": False, "locked": False, "version": 1
    })
    elements.append(text_box(start_x, start_y + 6, 80, 24, "开始", 16))

    steps = [
        ("旋转因子预计算\n(cos/sin查找表)", 180, 54),
        ("位反转排序\n(预计算索引表重排)", 180, 54),
        ("三层嵌套蝶形运算", 200, 54),
        ("实数FFT优化\n(N点实数→N/2点复数FFT)", 190, 54),
    ]

    box_w = 200
    x_center = start_x + 40 - box_w // 2
    y = start_y + 50
    prev_y_end = start_y + 36

    for i, (text, w, h) in enumerate(steps):
        x = start_x + 40 - w // 2
        if i == 2:
            bg = "#ffd43b"
            st = "#e8590c"
        else:
            bg = "#a5d8ff"
            st = "#1971c2"
        elements.append(rect(x, y, w, h, "", bg, st))
        elements.append(text_box(x, y + 6, w, h - 8, text, 13 if i == 2 else 14))
        elements.append(arrow(start_x + 40, prev_y_end, start_x + 40, y))
        prev_y_end = y + h
        y += h + 16

    # Sub-detail boxes for 蝶形运算
    sub_y = y - h - 16 + h + 6  # alongside the butterfly box, right side
    sub_steps = [
        ("外层: log₂(N)级", 150, 28),
        ("中间层: 每组蝶形数", 150, 28),
        ("内层: 单次蝶形运算\n1次复数乘法+2次复数加法", 160, 50),
    ]
    sub_x = start_x + 40 + w//2 + 25
    sub_start_y = prev_y_end - h + 5

    # Draw dashed arrow from butterfly box to sub-boxes area
    # and add sub-boxes vertically
    sub_y_pos = sub_start_y
    for j, (stext, sw, sh) in enumerate(sub_steps):
        elements.append(rect(sub_x, sub_y_pos, sw, sh, "", "#d0bfff", "#6741d9"))
        elements.append(text_box(sub_x, sub_y_pos + 2, sw, sh - 4, stext, 11))
        if j < len(sub_steps) - 1:
            elements.append(arrow(sub_x + sw//2, sub_y_pos + sh, sub_x + sw//2, sub_y_pos + sh + 8))
        sub_y_pos += sh + 10

    # End ellipse
    end_x = start_x + 40 - 40
    end_y = y + 10
    elements.append({
        "id": new_id(), "type": "ellipse", "x": end_x, "y": end_y, "width": 80, "height": 36,
        "strokeColor": "#2f9e44", "backgroundColor": "#b2f2bb", "fillStyle": "solid",
        "strokeWidth": 2, "roughness": 1, "opacity": 100,
        "roundness": {"type": 2}, "angle": 0, "groupIds": [], "frameId": None,
        "isDeleted": False, "locked": False, "version": 1
    })
    elements.append(text_box(end_x, end_y + 6, 80, 24, "结束", 16))
    elements.append(arrow(start_x + 40, prev_y_end, end_x + 40, end_y))

    make_excalidraw_file(elements, "fig3_fft_flowchart.excalidraw")


# ============================================================
# 图4 - 系统主程序流程 (Flowchart with loop)
# ============================================================
def gen_diagram4():
    elements = []

    elements.append(standalone_text(50, 10, "图4  系统主程序流程", 24))

    # Start
    start_x, start_y = 220, 65
    elements.append({
        "id": new_id(), "type": "ellipse", "x": start_x, "y": start_y, "width": 80, "height": 36,
        "strokeColor": "#1971c2", "backgroundColor": "#a5d8ff", "fillStyle": "solid",
        "strokeWidth": 2, "roughness": 1, "opacity": 100,
        "roundness": {"type": 2}, "angle": 0, "groupIds": [], "frameId": None,
        "isDeleted": False, "locked": False, "version": 1
    })
    elements.append(text_box(start_x, start_y + 6, 80, 24, "开始", 16))

    # Init block
    init_w, init_h = 180, 50
    init_x = start_x + 40 - init_w // 2
    init_y = start_y + 50
    elements.append(rect(init_x, init_y, init_w, init_h, "", "#eaddd8", "#5f3dc4"))
    elements.append(text_box(init_x, init_y + 6, init_w, init_h - 8, "系统初始化\n(DSP时钟/McBSP/ADC外设)", 13))
    elements.append(arrow(start_x + 40, start_y + 36, start_x + 40, init_y))

    # Main loop box (container-like)
    loop_w, loop_h = 180, 32
    loop_x = init_x
    loop_y = init_y + init_h + 20
    elements.append({
        "id": new_id(), "type": "diamond", "x": loop_x + 10, "y": loop_y, "width": loop_w - 20, "height": loop_h + 8,
        "strokeColor": "#e8590c", "backgroundColor": "#fff4e6", "fillStyle": "solid",
        "strokeWidth": 2, "roughness": 1, "opacity": 100,
        "roundness": {"type": 2}, "angle": 0, "groupIds": [], "frameId": None,
        "isDeleted": False, "locked": False, "version": 1
    })
    elements.append(arrow(init_x + init_w//2, init_y + init_h, loop_x + loop_w//2, loop_y))
    elements.append(text_box(loop_x + 10, loop_y + 8, loop_w - 20, 20, "主循环开始", 14))

    # Three steps in the loop
    loop_steps = [
        ("AD采集\n(DMA方式填充缓冲区)", "#a5d8ff", "#1971c2"),
        ("FFT处理\n(对N点数据执行\n基-2 DIT FFT)", "#b2f2bb", "#2f9e44"),
        ("频谱显示\n(更新CCS Graph窗口)", "#ffd43b", "#e8590c"),
    ]

    step_y = loop_y + loop_h//2 + 10
    step_x = loop_x + 20
    prev_bottom = loop_y + loop_h + 8

    step_centers = []
    for i, (stext, bg, st) in enumerate(loop_steps):
        sw, sh = 170, 54
        sx = step_x
        elements.append(rect(sx, step_y, sw, sh, "", bg, st))
        elements.append(text_box(sx, step_y + 4, sw, sh - 6, stext, 13))
        step_centers.append((sx + sw//2, step_y + sh//2))
        if i == 0:
            elements.append(arrow(loop_x + loop_w//2, prev_bottom, sx + sw//2, step_y))
        else:
            elements.append(arrow(prev_center[0], prev_center[1] + sh//2, sx + sw//2, step_y))
        prev_center = (sx + sw//2, step_y)
        prev_bottom = step_y + sh
        step_y += sh + 16

    # Loop back arrow
    last_step = loop_steps[-1]
    last_x = step_x
    last_y = step_y - 54 - 16  # last step y

    # Draw loop-back arrow on the right side
    loop_back_start_x = step_x + 170  # right edge of last step
    loop_back_start_y = last_y + 27  # middle of last step
    loop_bottom_y = last_y + 54 + 10

    # Arrow going right then down then left
    elements.append({
        "id": new_id(), "type": "arrow",
        "x": loop_back_start_x, "y": loop_back_start_y,
        "width": 0, "height": loop_bottom_y - loop_back_start_y + 10,
        "strokeColor": "#e8590c", "backgroundColor": "transparent", "fillStyle": "solid",
        "strokeWidth": 2, "roughness": 1, "opacity": 100,
        "roundness": {"type": 2}, "angle": 0, "groupIds": [], "frameId": None,
        "points": [[0, 0], [30, 0], [30, loop_bottom_y - loop_back_start_y + 10], [-80, loop_bottom_y - loop_back_start_y + 10]],
        "isDeleted": False, "locked": False, "version": 1
    })
    elements.append(arrow_label(last_x + 90, loop_bottom_y - 5, "循环", 12))

    # End
    end_x = start_x + 40 - 40
    end_y = loop_bottom_y + 30
    elements.append({
        "id": new_id(), "type": "ellipse", "x": end_x, "y": end_y, "width": 80, "height": 36,
        "strokeColor": "#2f9e44", "backgroundColor": "#b2f2bb", "fillStyle": "solid",
        "strokeWidth": 2, "roughness": 1, "opacity": 100,
        "roundness": {"type": 2}, "angle": 0, "groupIds": [], "frameId": None,
        "isDeleted": False, "locked": False, "version": 1
    })
    elements.append(text_box(end_x, end_y + 6, 80, 24, "结束", 16))

    # Arrow from loop diamond (left side) to end
    elements.append(arrow(loop_x, loop_y + loop_h//2, end_x + 80, end_y + 18))
    elements.append(arrow_label(loop_x - 50, loop_y + loop_h//2 - 18, "满足停止\n条件", 11))

    make_excalidraw_file(elements, "fig4_main_program_flow.excalidraw")


# ============================================================
# Generate all diagrams
# ============================================================
if __name__ == "__main__":
    gen_diagram1()
    gen_diagram2()
    gen_diagram3()
    gen_diagram4()
    print("\nAll 4 diagrams generated!")
