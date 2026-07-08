#!/usr/bin/env python3
"""整理 MediaCrawler 抓取数据，输出可读格式"""

import json
import os
import csv
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))

SRC_DIR = "MediaCrawler/data/xhs/jsonl"
OUT_DIR = "output/report_2026-06-07"
os.makedirs(OUT_DIR, exist_ok=True)

# ── 读取数据 ──
notes_by_id = {}
with open(f"{SRC_DIR}/search_contents_2026-06-07.jsonl", encoding="utf-8") as f:
    for line in f:
        n = json.loads(line)
        notes_by_id[n["note_id"]] = n

comments = []
with open(f"{SRC_DIR}/search_comments_2026-06-07.jsonl", encoding="utf-8") as f:
    for line in f:
        comments.append(json.loads(line))

comments_by_note = {}
for c in comments:
    nid = c["note_id"]
    comments_by_note.setdefault(nid, []).append(c)

def ts(ms):
    return datetime.fromtimestamp(ms / 1000, tz=TZ).strftime("%Y-%m-%d %H:%M")

def num_str(s):
    return s if s else "0"

def parse_like_count(s):
    """支持 1.3万 / 2108 / 空 等格式"""
    s = str(s).strip()
    if not s:
        return 0
    if "万" in s:
        return int(float(s.replace("万", "")) * 10000)
    return int(s)

# ── Markdown 报告 ──
md_path = f"{OUT_DIR}/小红书_编程副业兼职.md"
with open(md_path, "w", encoding="utf-8") as f:
    f.write("# 小红书搜索：编程副业 / 编程兼职\n\n")
    f.write(f"抓取时间：{datetime.now(TZ).strftime('%Y-%m-%d %H:%M')}\n")
    f.write(f"笔记数：{len(notes_by_id)}  |  评论数：{len(comments)}\n\n---\n\n")

    for i, (nid, note) in enumerate(notes_by_id.items(), 1):
        title = note.get("title", "无标题")
        desc = note.get("desc", "")
        nickname = note.get("nickname", "未知")
        likes = num_str(note.get("liked_count", "0"))
        collects = num_str(note.get("collected_count", "0"))
        comment_cnt = num_str(note.get("comment_count", "0"))
        shares = num_str(note.get("share_count", "0"))
        loc = note.get("ip_location", "")
        note_time = ts(note.get("time", 0))
        keyword = note.get("source_keyword", "")
        note_url = note.get("note_url", "")

        f.write(f"## {i}. {title}\n\n")
        f.write(f"| 字段 | 内容 |\n|------|------|\n")
        f.write(f"| 作者 | {nickname} |\n")
        f.write(f"| 地区 | {loc} |\n")
        f.write(f"| 发布时间 | {note_time} |\n")
        f.write(f"| 关键词 | {keyword} |\n")
        f.write(f"| ❤️ 点赞 | {likes} |\n")
        f.write(f"| ⭐ 收藏 | {collects} |\n")
        f.write(f"| 💬 评论 | {comment_cnt} |\n")
        f.write(f"| 🔄 分享 | {shares} |\n")
        f.write(f"| 链接 | {note_url} |\n")
        f.write(f"\n**正文：**\n\n{desc}\n\n")

        note_comments = comments_by_note.get(nid, [])
        if note_comments:
            note_comments.sort(key=lambda x: parse_like_count(x.get("like_count", "0")), reverse=True)
            top = note_comments[:10]
            f.write(f"<details>\n<summary>🔥 热门评论 TOP10（共{len(note_comments)}条）</summary>\n\n")
            for j, cmt in enumerate(top, 1):
                cmt_nick = cmt.get("nickname", "匿名")
                cmt_loc = cmt.get("ip_location", "")
                cmt_time = ts(cmt.get("create_time", 0))
                cmt_likes = cmt.get("like_count", "0")
                cmt_content = cmt.get("content", "")
                f.write(f"**{j}. {cmt_nick}**（{cmt_loc}） 👍{cmt_likes}  _{cmt_time}_\n\n")
                f.write(f"> {cmt_content}\n\n")
            f.write(f"</details>\n\n")

        f.write("---\n\n")

# ── CSV 列表 ──
csv_path = f"{OUT_DIR}/笔记列表.csv"
with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["序号", "标题", "作者", "地区", "发布时间", "点赞", "收藏", "评论数", "分享", "关键词", "链接"])
    for i, (nid, note) in enumerate(notes_by_id.items(), 1):
        w.writerow([
            i,
            note.get("title", ""),
            note.get("nickname", ""),
            note.get("ip_location", ""),
            ts(note.get("time", 0)),
            note.get("liked_count", ""),
            note.get("collected_count", ""),
            note.get("comment_count", ""),
            note.get("share_count", ""),
            note.get("source_keyword", ""),
            note.get("note_url", ""),
        ])

print(f"✅ 完成！文件已生成到 {OUT_DIR}/")
print(f"  - {md_path}")
print(f"  - {csv_path}")
