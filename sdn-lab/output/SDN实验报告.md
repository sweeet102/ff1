---
tags: [SDN, Ryu, Mininet, OpenFlow]
created: 2026-07-01
---

# SDN 实验报告

环境：Docker (Ubuntu 22.04) + Ryu 4.34 + Mininet 2.3.0 + OVS 2.17.9

---

## 实验一：二层自学习交换机

**代码**：`app/e1_switch.py`

**拓扑**：1 台交换机 + 4 台主机，控制器远程模式

**运行方式**：

窗口 1：`ryu-manager --verbose app/e1_switch.py`
窗口 2：`python3 app/e1_topo.py`
窗口 3：`ovs-ofctl -O OpenFlow13 dump-flows s1`

**关键结果**：

- pingall：**12/12，0% 丢包**
- 流表包含 **12 条精确 MAC 转发表** + 1 条 table-miss 默认流表
- 每条规则格式：`dl_src=MAC, dl_dst=MAC → output:端口`
- Wireshark 抓包可看到完整 OpenFlow 协议交互：Hello → Feature Request/Reply → FlowMod → PacketIn → PacketOut

**原理**：控制器通过 MAC 地址自学习建立转发表。未知目的 MAC 泛洪，已知的下发精确流表，后续包由硬件直接转发。

![实验一 L2 交换机](screenshots/exp1.png)

---

## 实验二 L3：三层 IP 交换

**代码**：`app/l3switch.py`

**拓扑**：1 交换机 + 4 主机

**运行方式**：

窗口 1：`ryu-manager --verbose app/l3switch.py`
窗口 2：`python3 app/e2_l3.py`
窗口 3：`ovs-ofctl -O OpenFlow13 dump-flows s1`

**关键结果**：

- pingall：**12/12，0% 丢包**
- TCP iperf h1→h4：**102 Gbits/sec**
- 流表匹配字段从 L2 的 `dl_src/dl_dst` 扩展到 **`ip,nw_src,nw_dst`**

**对比 L2**：流表新增 IP 层匹配，可以对不同 IP 流做不同转发策略。

![实验二 L3 三层交换](screenshots/exp2_l3.png)

---

## 实验二 L4：四层 TCP/UDP/ICMP 交换

**代码**：`app/l4switch.py`

**拓扑**：1 交换机 + 4 主机

**运行方式**：

窗口 1：`ryu-manager --verbose app/l4switch.py`
窗口 2：`python3 app/e2_l4.py`
窗口 3：`ovs-ofctl -O OpenFlow13 dump-flows s1`

**关键结果**：

- pingall：**12/12，0% 丢包**（ICMP）
- TCP iperf h4→h1：**105 Gbits/sec**
- UDP iperf h3→h2：**1.06 Mbits/sec，丢包率 0%**
- 流表区分三种协议：
  - ICMP：`icmp,nw_src=...,nw_dst=...`
  - TCP：`tcp,nw_src=...,nw_dst=...,tp_src=5001,tp_dst=xxxxx`
  - UDP：`udp,...`

**三层对比**：

| 层次 | 匹配字段 |
|------|----------|
| L2（实验一） | `dl_src, dl_dst` |
| L3（实验二-L3） | `ip, nw_src, nw_dst` |
| L4（实验二-L4） | `tcp/udp/icmp, nw_src, nw_dst, tp_src, tp_dst` |

![实验二 L4 四层交换](screenshots/exp2_l4.png)

---

## 实验三：多表流水线 — ICMP 过滤

**代码**：`app/multiple_tables.py`

**拓扑**：1 交换机 + 4 主机

**运行方式**：

窗口 1：`ryu-manager --verbose app/multiple_tables.py`
窗口 2：`python3 app/exp3_mininet.py`（TCP iperf + ping 测试）
窗口 3：
```bash
ovs-ofctl -O OpenFlow13 dump-flows s1 table=0
ovs-ofctl -O OpenFlow13 dump-flows s1 table=5
ovs-ofctl -O OpenFlow13 dump-flows s1 table=10
```

**关键结果**：

| 测试项 | 结果 | 原因 |
|--------|------|------|
| TCP iperf h1→h4 | ✅ **通**，105 Gbits/sec | TCP 匹配 Table 5 `priority=1` → Goto Table 10 正常转发 |
| ping h1→h4 | ❌ **不通，100% 丢包** | ICMP 匹配 Table 5 `priority=10000` → DROP |
| ping h2→h3 | ❌ **也不通** | 同上，所有 ICMP 都被 DROP |

**三表流水线**：

```
Table 0                 Table 5                   Table 10
┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
│ priority=0   │──→    │ ICMP priority=10k │──→ ✕  │ L2 forwarding│
│ ALL → Goto 5 │       │ → DROP (空指令)   │       │ MAC learning │
└──────────────┘       │                  │       │              │
                       │ 其他 priority=1  │──→    │ priority=1   │
                       │ → Goto 10        │       │ 精确转发     │
                       └──────────────────┘       └──────────────┘
```

**核心原理**：

1. **Table 5 有两条规则**：ICMP 规则 `priority=10000`，其他流量 `priority=1`。ICMP 进来匹配高优先级，指令列表为空 → **静默丢弃**
2. TCP/UDP 不匹配 ICMP 规则，命中 `priority=1` → **Goto Table 10** 正常转发
3. 这展示了 OpenFlow 的**多表流水线**能力——不同表做不同事情，先过滤再转发，硬件实现

**对应实验指导书图 2.4 的效果**：h1 与 h4 能建立 TCP 连接，但无法 ping 通，流表中可见一条超高优先级的 ICMP DROP 规则。

![实验三 多表流水线]()

---

（实验四 ~ 实验六待补充）

---

> 下次实验继续更新本文档。截图放在 `output/screenshots/` 目录下。
