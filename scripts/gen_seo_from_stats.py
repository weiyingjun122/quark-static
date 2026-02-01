#!/usr/bin/env python3
"""
SEO页面生成脚本 - GitHub Pages版本
直接从Cloudflare KV获取统计，生成SEO页面到search目录
"""

import json
import os
import re
import requests
import time
from datetime import datetime
from urllib.parse import quote

# ==================== 配置 ====================
CONFIG = {
    # Cloudflare KV API配置（从你的[[path]].js获取）
    "cloudflare": {
        "site_url": "https://search.weiyingjun.top",  # 你的Cloudflare Pages域名
        "sync_endpoint": "/api/sync",
        "sync_key": "my_secret_sync_key"  # 必须与[[path]].js中的一致
    },
    
    # 本地文件配置
    "files": {
        "data_json": "data.json",          # 资源数据
        "output_dir": "search",            # 输出目录（GitHub Pages会自动发布）
        "stats_backup": "stats_backup.json" # 统计备份
    },
    
    # SEO配置
    "seo": {
        "min_search_count": 10,            # 最小搜索次数
        "max_pages_per_keyword": 1,        # 每个关键词生成1个页面
        "max_resources_per_page": 15,      # 每页最多显示资源数
        "site_name": "夸克网盘资源搜索",
        "site_url": "https://search.weiyingjun.top",
        "description": "免费提供夸克网盘资源搜索下载服务",
        "keywords": "夸克网盘,资源下载,网盘搜索,免费资源"
    }
}

# ==================== HTML模板 ====================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{keyword}资源下载 - {site_name}</title>
    <meta name="description" content="免费提供{keyword}相关资源下载，包含{resource_count}个{keyword}相关资源，夸克网盘高速下载。">
    <meta name="keywords" content="{keyword},夸克网盘,{keyword}下载,{keyword}资源,网盘分享">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="{site_url}/search/{filename}">
    
    <!-- Open Graph -->
    <meta property="og:title" content="{keyword}资源下载 - {site_name}">
    <meta property="og:description" content="免费下载{keyword}相关资源，共{resource_count}个资源">
    <meta property="og:url" content="{site_url}/search/{filename}">
    <meta property="og:type" content="website">
    
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{keyword}资源下载">
    <meta name="twitter:description" content="免费{keyword}资源下载">
    
    <!-- JSON-LD 结构化数据 -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "{keyword}资源下载",
        "description": "提供{keyword}相关资源下载服务",
        "url": "{site_url}/search/{filename}",
        "datePublished": "{publish_date}",
        "dateModified": "{update_time}",
        "mainEntity": {{
            "@type": "ItemList",
            "numberOfItems": {resource_count},
            "itemListElement": [
                {resource_schema_items}
            ]
        }}
    }}
    </script>
    
    <style>
        /* 基础样式 */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f8f9fa;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        /* 头部样式 */
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .keyword-title {{
            font-size: 32px;
            margin-bottom: 15px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        .stats {{
            font-size: 18px;
            opacity: 0.9;
            margin-top: 10px;
        }}
        
        /* 搜索框 */
        .search-box {{
            text-align: center;
            margin: 30px 0;
        }}
        .search-btn {{
            background: #007bff;
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 50px;
            font-size: 18px;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 4px 15px rgba(0,123,255,0.3);
        }}
        .search-btn:hover {{
            background: #0056b3;
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,123,255,0.4);
        }}
        
        /* 资源列表 */
        .resources {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            margin: 30px 0;
        }}
        .section-title {{
            font-size: 24px;
            color: #333;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
        }}
        .resource-item {{
            padding: 20px;
            margin: 15px 0;
            border-radius: 10px;
            background: #f8f9fa;
            border-left: 4px solid #007bff;
            transition: all 0.3s;
        }}
        .resource-item:hover {{
            background: #e3f2fd;
            transform: translateX(5px);
        }}
        .resource-title {{
            font-size: 18px;
            color: #333;
            margin-bottom: 10px;
            font-weight: 600;
        }}
        .resource-link {{
            color: #007bff;
            text-decoration: none;
            font-size: 14px;
            word-break: break-all;
            display: block;
            margin: 10px 0;
        }}
        .resource-link:hover {{
            text-decoration: underline;
        }}
        .highlight {{
            color: #e74c3c;
            font-weight: bold;
            background: #ffebee;
            padding: 2px 5px;
            border-radius: 3px;
        }}
        
        /* 页脚 */
        .footer {{
            text-align: center;
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #666;
            font-size: 14px;
        }}
        
        /* 响应式 */
        @media (max-width: 768px) {{
            body {{ padding: 10px; }}
            .header {{ padding: 25px 15px; }}
            .keyword-title {{ font-size: 24px; }}
            .resources {{ padding: 15px; }}
            .resource-item {{ padding: 15px; }}
        }}
    </style>
</head>
<body>
    <!-- 头部 -->
    <div class="header">
        <h1 class="keyword-title">"{keyword}" 资源免费下载</h1>
        <div class="stats">
            🔥 搜索热度: {search_count}次 | 📁 相关资源: {resource_count}个
        </div>
    </div>
    
    <!-- 搜索按钮 -->
    <div class="search-box">
        <a href="/?q={keyword_encoded}">
            <button class="search-btn">
                🔍 搜索更多"{keyword}"资源
            </button>
        </a>
    </div>
    
    <!-- 资源列表 -->
    <div class="resources">
        <h2 class="section-title">📚 相关资源列表</h2>
        {resource_items}
    </div>
    
    <!-- 返回首页 -->
    <div class="search-box">
        <a href="/">
            <button class="search-btn" style="background: #6c757d;">
                🏠 返回首页搜索更多资源
            </button>
        </a>
    </div>
    
    <!-- 页脚 -->
    <div class="footer">
        <p>© {current_year} {site_name} | 最后更新: {update_time}</p>
        <p>本页面为热门搜索关键词自动生成，内容持续更新</p>
        <p style="margin-top: 10px;">
            <a href="/search/">查看所有热门关键词</a> | 
            <a href="/">返回首页</a>
        </p>
    </div>
</body>
</html>
"""

# ==================== 核心函数 ====================

def get_stats_from_cloudflare():
    """从Cloudflare KV获取统计信息"""
    try:
        url = f"{CONFIG['cloudflare']['site_url']}{CONFIG['cloudflare']['sync_endpoint']}"
        params = {"key": CONFIG['cloudflare']['sync_key']}
        
        print(f"🌐 正在从Cloudflare获取统计...")
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ 获取成功: {len(stats)} 个关键词")
            return stats
        else:
            print(f"❌ 获取失败: HTTP {response.status_code}")
            return {}
            
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return {}

def load_resources():
    """加载资源数据"""
    try:
        with open(CONFIG['files']['data_json'], 'r', encoding='utf-8') as f:
            resources = json.load(f)
        print(f"📁 加载资源: {len(resources)} 个")
        return resources
    except Exception as e:
        print(f"❌ 加载资源失败: {e}")
        return []

def find_matching_resources(keyword, resources):
    """查找匹配关键词的资源"""
    matched = []
    keyword_lower = keyword.lower()
    
    for resource in resources:
        # 在title中搜索
        title = resource.get('title', '').lower()
        if keyword_lower in title:
            matched.append(resource)
            continue
            
        # 在keywords数组中搜索
        keywords = resource.get('keywords', [])
        if isinstance(keywords, list):
            if any(keyword_lower in str(k).lower() for k in keywords):
                matched.append(resource)
        elif isinstance(keywords, str):
            if keyword_lower in keywords.lower():
                matched.append(resource)
    
    return matched

def generate_seo_page(keyword, search_count, resources):
    """生成单个关键词的SEO页面"""
    # 查找匹配资源
    matched_resources = find_matching_resources(keyword, resources)
    
    if not matched_resources:
        return None
    
    # 限制资源数量
    display_resources = matched_resources[:CONFIG['seo']['max_resources_per_page']]
    
    # 生成资源列表HTML
    resource_items = ""
    resource_schema_items = []
    
    for i, resource in enumerate(display_resources, 1):
        title = resource.get('title', '未命名资源')
        link = resource.get('share_link', '#')
        
        # 高亮关键词
        highlighted_title = re.sub(
            f'({re.escape(keyword)})',
            r'<span class="highlight">\1</span>',
            title,
            flags=re.IGNORECASE
        )
        
        # 资源项HTML
        resource_items += f'''
        <div class="resource-item">
            <div class="resource-title">{i}. {highlighted_title}</div>
            <a href="{link}" class="resource-link" target="_blank" rel="nofollow noopener">
                🔗 资源链接: {link}
            </a>
        </div>'''
        
        # 结构化数据项
        schema_item = {{
            "@type": "ListItem",
            "position": i,
            "item": {{
                "@type": "DigitalDocument",
                "name": title,
                "url": link
            }}
        }}
        resource_schema_items.append(json.dumps(schema_item, ensure_ascii=False))
    
    # 生成安全的文件名
    safe_filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', keyword)
    safe_filename = re.sub(r'\s+', '_', safe_filename.strip())
    if not safe_filename:
        safe_filename = f"keyword_{hash(keyword) % 10000}"
    safe_filename += ".html"
    
    # URL编码关键词（用于搜索链接）
    keyword_encoded = quote(keyword)
    
    # 准备数据
    now = datetime.now()
    data = {
        'keyword': keyword,
        'keyword_encoded': keyword_encoded,
        'site_name': CONFIG['seo']['site_name'],
        'site_url': CONFIG['seo']['site_url'],
        'filename': safe_filename,
        'search_count': search_count,
        'resource_count': len(matched_resources),
        'resource_items': resource_items,
        'resource_schema_items': ',\n                '.join(resource_schema_items),
        'publish_date': now.strftime('%Y-%m-%d'),
        'update_time': now.strftime('%Y-%m-%d %H:%M'),
        'current_year': now.year
    }
    
    # 生成HTML
    html_content = HTML_TEMPLATE.format(**data)
    
    # 保存文件
    output_path = os.path.join(CONFIG['files']['output_dir'], safe_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return {
        'keyword': keyword,
        'count': search_count,
        'resources': len(matched_resources),
        'file': safe_filename,
        'path': output_path
    }

def generate_index_page(generated_pages):
    """生成关键词索引页面"""
    index_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>热门搜索关键词 - 夸克网盘资源</title>
    <meta name="description" content="根据用户搜索热度自动生成的热门关键词资源页面，包含热门资源的直接下载链接。">
    <meta name="robots" content="index, follow">
    <style>
        body {
            font-family: 'Microsoft YaHei', sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f7fa;
        }
        .header {
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 15px;
            margin-bottom: 40px;
        }
        .title {
            font-size: 36px;
            margin-bottom: 15px;
        }
        .subtitle {
            font-size: 18px;
            opacity: 0.9;
        }
        .stats {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: 15px;
        }
        .stat-item {
            text-align: center;
            flex: 1;
            min-width: 150px;
        }
        .stat-number {
            font-size: 28px;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }
        .keywords-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .keyword-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 3px 15px rgba(0,0,0,0.1);
            transition: all 0.3s;
        }
        .keyword-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
        }
        .keyword-title {
            font-size: 20px;
            margin-bottom: 15px;
        }
        .keyword-title a {
            color: #333;
            text-decoration: none;
        }
        .keyword-title a:hover {
            color: #667eea;
        }
        .keyword-meta {
            display: flex;
            justify-content: space-between;
            margin-top: 15px;
            font-size: 14px;
            color: #666;
        }
        .search-count {
            background: #ff6b6b;
            color: white;
            padding: 3px 10px;
            border-radius: 15px;
        }
        .resource-count {
            background: #4ecdc4;
            color: white;
            padding: 3px 10px;
            border-radius: 15px;
        }
        .footer {
            text-align: center;
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #666;
            font-size: 14px;
        }
        @media (max-width: 768px) {
            .keywords-grid {
                grid-template-columns: 1fr;
            }
            .stat-item {
                min-width: 120px;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">🔥 热门搜索关键词</h1>
        <p class="subtitle">根据用户搜索热度自动生成的资源页面</p>
    </div>
    
    <div class="stats">
        <div class="stat-item">
            <div class="stat-number">''' + str(len(generated_pages)) + '''</div>
            <div class="stat-label">热门关键词</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">''' + str(sum(p['count'] for p in generated_pages)) + '''</div>
            <div class="stat-label">总搜索次数</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">''' + str(sum(p['resources'] for p in generated_pages)) + '''</div>
            <div class="stat-label">总资源数</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">''' + datetime.now().strftime('%m-%d') + '''</div>
            <div class="stat-label">更新日期</div>
        </div>
    </div>
    
    <div class="keywords-grid">
'''
    
    # 按搜索次数排序
    sorted_pages = sorted(generated_pages, key=lambda x: x['count'], reverse=True)
    
    for page in sorted_pages:
        index_content += f'''
        <div class="keyword-card">
            <h3 class="keyword-title">
                <a href="{page['file']}">{page['keyword']}</a>
            </h3>
            <div class="keyword-meta">
                <span class="search-count">🔥 {page['count']}次搜索</span>
                <span class="resource-count">📁 {page['resources']}个资源</span>
            </div>
        </div>'''
    
    index_content += f'''
    </div>
    
    <div class="footer">
        <p>© {datetime.now().year} {CONFIG['seo']['site_name']}</p>
        <p>最后生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p style="margin-top: 15px;">
            <a href="/">返回首页</a> | 
            <a href="https://github.com/your-repo" target="_blank">GitHub仓库</a>
        </p>
    </div>
</body>
</html>'''
    
    output_path = os.path.join(CONFIG['files']['output_dir'], "index.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(index_content)
    
    return output_path

def main():
    """主函数"""
    print("=" * 60)
    print("📱 SEO页面生成器 - GitHub Pages版本")
    print("=" * 60)
    
    # 1. 创建输出目录
    output_dir = CONFIG['files']['output_dir']
    os.makedirs(output_dir, exist_ok=True)
    print(f"📂 输出目录: {output_dir}")
    
    # 2. 从Cloudflare获取统计
    print("\n1️⃣ 获取搜索统计...")
    stats = get_stats_from_cloudflare()
    
    if not stats:
        print("⚠️  无法获取统计，使用空数据继续")
        stats = {}
    
    # 3. 加载资源
    print("\n2️⃣ 加载资源数据...")
    resources = load_resources()
    
    if not resources:
        print("❌ 没有资源数据，停止执行")
        return
    
    # 4. 筛选热门关键词
    print(f"\n3️⃣ 筛选热门关键词（≥{CONFIG['seo']['min_search_count']}次）...")
    hot_keywords = []
    
    for keyword, count in stats.items():
        if count >= CONFIG['seo']['min_search_count']:
            hot_keywords.append((keyword, count))
    
    hot_keywords.sort(key=lambda x: x[1], reverse=True)
    
    if not hot_keywords:
        print(f"⚠️  没有达到{CONFIG['seo']['min_search_count']}次搜索的关键词")
        return
    
    print(f"✅ 发现 {len(hot_keywords)} 个热门关键词")
    
    # 5. 生成页面
    print(f"\n4️⃣ 生成SEO页面...")
    generated = []
    
    for keyword, count in hot_keywords:
        print(f"  处理: '{keyword}' ({count}次搜索)")
        
        result = generate_seo_page(keyword, count, resources)
        if result:
            generated.append(result)
            print(f"    ✅ 生成成功: {result['resources']}个资源")
        else:
            print(f"    ⚠️  无匹配资源，跳过")
    
    # 6. 生成索引页
    if generated:
        print(f"\n5️⃣ 生成索引页面...")
        index_path = generate_index_page(generated)
        print(f"   ✅ 索引页: {index_path}")
        
        # 7. 生成sitemap
        print(f"\n6️⃣ 生成站点地图...")
        generate_sitemap(generated)
        
        # 8. 输出统计
        print(f"\n" + "=" * 60)
        print(f"🎉 生成完成！")
        print(f"📊 统计信息:")
        print(f"   • 热门关键词: {len(generated)} 个")
        print(f"   • 总搜索次数: {sum(p['count'] for p in generated)} 次")
        print(f"   • 总资源数: {sum(p['resources'] for p in generated)} 个")
        print(f"   • 输出目录: {output_dir}/")
        print(f"\n🚀 页面已生成，提交到GitHub即可自动发布到GitHub Pages")
        
        # 9. 保存备份
        backup_stats(stats, generated)
        
    else:
        print("\n❌ 没有生成任何页面")

def generate_sitemap(generated_pages):
    """生成sitemap.xml"""
    sitemap = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>''' + CONFIG['seo']['site_url'] + '''/</loc>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>''' + CONFIG['seo']['site_url'] + '''/search/</loc>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>'''
    
    for page in generated_pages:
        sitemap += f'''
    <url>
        <loc>{CONFIG['seo']['site_url']}/search/{page['file']}</loc>
        <changefreq>weekly</changefreq>
        <priority>0.7</priority>
    </url>'''
    
    sitemap += '''
</urlset>'''
    
    sitemap_path = os.path.join(CONFIG['files']['output_dir'], "sitemap.xml")
    with open(sitemap_path, 'w', encoding='utf-8') as f:
        f.write(sitemap)
    
    print(f"   ✅ 站点地图: {sitemap_path}")

def backup_stats(stats, generated_pages):
    """备份统计信息"""
    backup = {
        "timestamp": datetime.now().isoformat(),
        "total_keywords": len(stats),
        "hot_keywords_count": len(generated_pages),
        "stats_summary": stats,
        "generated_pages": generated_pages,
        "config": CONFIG
    }
    
    backup_path = CONFIG['files']['stats_backup']
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(backup, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"   💾 统计备份: {backup_path}")

if __name__ == "__main__":
    main()