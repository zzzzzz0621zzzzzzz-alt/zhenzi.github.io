#!/usr/bin/env python3
import json
import urllib.request
import urllib.parse
import time
from datetime import datetime

keywords = [
    "中山一院 康复医学科",
    "中山一院 何冠蘅",
    "中山一院 陈佩妍",
    "中山一院 吴俊林",
    "中山一院 邹德志",
    "中山一院 李怡"
]

def fetch_videos(keyword):
    url = f"https://api.bilibili.com/x/web-interface/search/all/v2?keyword={urllib.parse.quote(keyword)}"
    print(f"Fetching: {keyword}")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.load(response)
            if data['code'] != 0:
                print(f"  API error: {data.get('message')}")
                return []
            results = data['data']['result']
            for res in results:
                if res.get('result_type') == 'video':
                    videos = res.get('data', [])
                    return videos
            return []
    except Exception as e:
        print(f"  Error: {e}")
        return []

def timestamp_to_date(ts):
    try:
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    except:
        return str(ts)

def main():
    all_results = {}
    for kw in keywords:
        videos = fetch_videos(kw)
        all_results[kw] = videos
        time.sleep(1)  # be polite
    
    # Generate markdown
    md_lines = []
    md_lines.append("# 中山一院B站视频搜索结果")
    md_lines.append("")
    md_lines.append(f"搜索时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}")
    md_lines.append("")
    
    for kw, videos in all_results.items():
        md_lines.append(f"## {kw}")
        md_lines.append("")
        if not videos:
            md_lines.append("未找到相关视频。")
            md_lines.append("")
            continue
        md_lines.append("### 找到的视频：")
        md_lines.append("")
        for i, vid in enumerate(videos[:20], 1):  # limit to 20 per keyword
            title = vid.get('title', '').replace('<em class=\"keyword\">', '').replace('</em>', '')
            author = vid.get('author', '')
            arcurl = vid.get('arcurl', '')
            pubdate = timestamp_to_date(vid.get('pubdate', 0))
            duration = vid.get('duration', '')
            description = vid.get('description', '').strip()
            if description == '-' or not description:
                description = ''
            md_lines.append(f"{i}. **{title}**")
            md_lines.append(f"   - 视频标题：{title}")
            md_lines.append(f"   - 视频描述：{description}")
            md_lines.append(f"   - 上传者/作者：{author}")
            md_lines.append(f"   - 视频链接：{arcurl}")
            md_lines.append(f"   - 发布日期：{pubdate}")
            md_lines.append(f"   - 视频时长：{duration}")
            md_lines.append("")
        md_lines.append("")
    
    md_lines.append("## 总结")
    md_lines.append("")
    md_lines.append("- 以上视频通过B站搜索API获取，结果可能不完整。")
    md_lines.append("- 视频链接为B站视频页面链接，可直接访问。")
    md_lines.append("- 如需更多结果，可调整搜索关键词或直接访问B站搜索。")
    
    output_path = "findings_bilibili.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))
    print(f"结果已保存到 {output_path}")

if __name__ == '__main__':
    main()