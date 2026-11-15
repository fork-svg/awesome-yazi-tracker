#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Awesome Yazi Plugin Tracker
自动抓取 awesome-yazi 列表中所有插件的 Star 数和更新时间
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

# 配置
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUTPUT_DIR = Path("data")
README_PATH = Path("README.md")
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}
AWESOME_YAZI_REPO = "AnirudhG07/awesome-yazi"


def fetch_awesome_yazi_readme():
    """获取 awesome-yazi 的 README 内容"""
    print("获取 awesome-yazi README...")
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{AWESOME_YAZI_REPO}/readme",
            headers=HEADERS,
            timeout=15
        )
        resp.raise_for_status()
        return resp.json().get("content", "")
    except Exception as e:
        print(f"获取 README 失败: {e}")
        return None


def extract_github_repos(readme_content):
    """从 README 中提取所有 GitHub 仓库链接"""
    import base64
    try:
        content = base64.b64decode(readme_content).decode("utf-8")
    except:
        content = readme_content

    # 匹配 GitHub 仓库链接
    pattern = r'github\.com/([a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+)'
    matches = re.findall(pattern, content)

    repos = set()
    for match in matches:
        # 清理链接
        repo = match.rstrip('.').rstrip('/')
        # 排除非插件仓库
        if repo in ['sxyazi/yazi', 'AnirudhG07/awesome-yazi']:
            continue
        # 只保留 yazi 相关的仓库（包含 .yazi 或 yazi 在名称中）
        if '.yazi' in repo or 'yazi' in repo.lower():
            repos.add(repo)
        # 也包含插件集合仓库
        elif 'plugins' in repo.lower():
            repos.add(repo)

    return sorted(repos)


def fetch_repo_info(repo_name):
    """获取仓库的 star 数和更新时间"""
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{repo_name}",
            headers=HEADERS,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "name": repo_name,
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "updated_at": data.get("pushed_at", ""),
                "created_at": data.get("created_at", ""),
                "description": data.get("description", ""),
                "language": data.get("language", ""),
                "url": data.get("html_url", f"https://github.com/{repo_name}"),
            }
        elif resp.status_code == 403:
            print(f"  ⚠️ API 限制，等待...")
            time.sleep(5)
            return None
        else:
            print(f"  ❌ {repo_name}: {resp.status_code}")
            return None
    except Exception as e:
        print(f"  ❌ {repo_name}: {e}")
        return None


def load_existing_data():
    """加载已有数据"""
    data_file = OUTPUT_DIR / "plugins.json"
    if data_file.exists():
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"plugins": [], "last_update": None}


def save_data(data):
    """保存数据"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    data_file = OUTPUT_DIR / "plugins.json"
    data["last_update"] = datetime.now(timezone.utc).isoformat()
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_readme(data):
    """生成 README.md"""
    plugins = data.get("plugins", [])

    # 按 star 数排序
    plugins_sorted = sorted(plugins, key=lambda x: x.get("stars", 0), reverse=True)

    # 计算统计
    total_stars = sum(p.get("stars", 0) for p in plugins)
    avg_stars = total_stars / len(plugins) if plugins else 0

    readme = f"""# 🦆 Awesome Yazi Plugin Tracker

自动追踪 [awesome-yazi](https://github.com/AnirudhG07/awesome-yazi) 中所有插件的 Star 数和活跃度。

**更新频率**: 每周自动更新

**最后更新**: {(data.get("last_update") or "N/A")[:19].replace("T", " ")}

---

## 📊 统计

| 指标 | 数值 |
|------|------|
| 插件总数 | **{len(plugins)}** |
| 总 Star 数 | **{total_stars:,}** |
| 平均 Star 数 | **{avg_stars:.1f}** |

---

## 🏆 插件排行榜 (按 Star 排序)

| # | 插件 | Stars | Forks | 语言 | 最后更新 | 描述 |
|---|------|------:|------:|------|----------|------|
"""

    for i, p in enumerate(plugins_sorted, 1):
        name = p.get("name", "")
        short_name = name.split("/")[-1] if "/" in name else name
        url = p.get("url", f"https://github.com/{name}")
        link = f"[{short_name}]({url})"

        stars = p.get("stars", 0)
        forks = p.get("forks", 0)
        lang = p.get("language", "") or "-"
        updated = p.get("updated_at", "")[:10] or "-"
        desc = p.get("description", "") or "-"
        if len(desc) > 50:
            desc = desc[:47] + "..."

        readme += f"| {i} | {link} | ⭐ {stars:,} | 🍴 {forks} | {lang} | {updated} | {desc} |\n"

    readme += """
---

## 📈 活跃度分析

### 最近 30 天更新的插件
"""

    # 最近 30 天活跃的插件
    now = datetime.now(timezone.utc)
    recent = []
    for p in plugins_sorted:
        updated_str = p.get("updated_at", "")
        if updated_str:
            try:
                updated_dt = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
                if (now - updated_dt).days <= 30:
                    recent.append(p)
            except:
                pass

    if recent:
        readme += f"\n最近 30 天内有 **{len(recent)}** 个插件更新：\n\n"
        for p in recent[:10]:
            name = p.get("name", "").split("/")[-1]
            updated = p.get("updated_at", "")[:10]
            readme += f"- [{name}]({p.get('url', '')}) - 更新于 {updated}\n"
    else:
        readme += "\n暂无最近 30 天内的更新\n"

    readme += """
---

## ⚙️ 工作原理

1. 每周通过 GitHub Actions 自动运行
2. 解析 awesome-yazi 的 README
3. 提取所有 GitHub 插件链接
4. 通过 GitHub API 获取 Star 数、Fork 数、最后更新时间
5. 生成排行榜并更新 README

---

## 🔗 相关链接

- [awesome-yazi](https://github.com/AnirudhG07/awesome-yazi) - 原始插件列表
- [Yazi](https://github.com/sxyazi/yazi) - 终端文件管理器

---

*Last updated: """ + (data.get("last_update") or "N/A") + "*"

    with open(README_PATH, 'w', encoding='utf-8') as f:
        f.write(readme)


def main():
    print("=" * 50)
    print("🦆 Awesome Yazi Plugin Tracker")
    print("=" * 50)

    # 获取 README
    readme_content = fetch_awesome_yazi_readme()
    if not readme_content:
        print("无法获取 README，退出")
        return

    # 提取仓库链接
    repos = extract_github_repos(readme_content)
    print(f"\n发现 {len(repos)} 个插件仓库\n")

    # 加载已有数据
    data = load_existing_data()
    existing = {p.get("name") for p in data.get("plugins", [])}

    # 获取每个仓库的信息
    new_plugins = []
    for repo in repos:
        if repo in existing:
            print(f"  ✓ 已存在: {repo}")
            # 从已有数据中获取
            for p in data["plugins"]:
                if p.get("name") == repo:
                    new_plugins.append(p)
                    break
            continue

        print(f"  📦 获取: {repo}")
        info = fetch_repo_info(repo)
        if info:
            new_plugins.append(info)
            print(f"    ⭐ {info['stars']:,} | 🍴 {info['forks']} | {info['updated_at'][:10]}")
        else:
            # API 失败时保留默认值
            new_plugins.append({
                "name": repo,
                "stars": 0,
                "forks": 0,
                "updated_at": "",
                "description": "",
                "language": "",
                "url": f"https://github.com/{repo}",
            })

        time.sleep(0.5)  # 避免 API 限制

    # 保存数据
    data["plugins"] = new_plugins
    save_data(data)

    print(f"\n✅ 共 {len(new_plugins)} 个插件")

    # 生成 README
    generate_readme(data)
    print("✅ README.md 已更新")


if __name__ == "__main__":
    main()
