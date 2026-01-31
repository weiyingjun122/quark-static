import json
import os

STATS_FILE = "static/stats.json"
OUT_DIR = "search"
DOMAIN = "https://search.weiyingjun.top"   # ← 改成你的

MIN_COUNT = 10   # ⭐ 只要 >=10 次的热搜

tpl = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{kw} 资源免费下载｜夸克网盘</title>
<meta name="description" content="提供 {kw} 相关夸克网盘资源免费下载入口，持续更新。">
<meta name="keywords" content="{kw},夸克网盘,{kw}下载">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{domain}/search/{kw}.html">
</head>
<body>
<h1>{kw} 资源合集</h1>
<p>正在为你跳转到 {kw} 搜索结果页…</p>
<script>
location.href='/?q={kw}';
</script>
</body>
</html>
"""

if not os.path.exists(STATS_FILE):
    print("❌ stats.json 不存在")
    exit(0)

with open(STATS_FILE, "r", encoding="utf-8") as f:
    stats = json.load(f)

keywords = stats.get("search_keywords", {})

os.makedirs(OUT_DIR, exist_ok=True)

count = 0
for kw, v in keywords.items():
    if v.get("count", 0) < MIN_COUNT:
        continue

    path = os.path.join(OUT_DIR, f"{kw}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(tpl.format(kw=kw, domain=DOMAIN))
    count += 1

print(f"✅ 生成 SEO 页面：{count} 个")
