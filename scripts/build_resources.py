import pandas as pd
import qrcode
import os
import json

# 获取脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))

# Excel 路径（同级）
excel_path = os.path.join(script_dir, r"D:\Download\quark-static\resources.xlsx")

# 输出二维码目录
output_dir = os.path.join(script_dir, "..", "static", "qrcode")
os.makedirs(output_dir, exist_ok=True)

# 输出 JSON 文件
json_path = os.path.join(script_dir, "..", "data.json")

# 读取 Excel
df = pd.read_excel(excel_path)

# 存放 JSON 数据
index = []

for _, r in df.iterrows():
    # 生成二维码
    img = qrcode.make(r['share_link'])
    save_path = os.path.join(output_dir, f"{r['id']}.png")
    img.save(save_path)
    print(f"生成二维码: {save_path}")

    # 构建 JSON
    index.append({
        "id": str(r['id']),
        "title": r['title'],
        "keywords": [k.strip() for k in r['keywords'].split(",")],
        "share_link": r['share_link'],
        "qrcode": f"static/qrcode/{r['id']}.png"
    })

# 写入 JSON
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

print(f"data.json 已生成: {json_path}")
print("所有资源生成完成！")
