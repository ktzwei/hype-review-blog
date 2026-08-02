#!/usr/bin/env python3
"""
HYPE 每日价格复盘 → GitHub Pages 博客生成器

用法:
  .venv/bin/python publish.py report-2026-08-01.md "2026.08.01" --push

作用:
  1. 把单日复盘 markdown 渲染成 reports/YYYY-MM-DD.html (深色博客风格, 图片内嵌 base64)
  2. 更新 index.html 目录, 列出所有复盘
  3. (可选) git add/commit/push

图片: markdown 里用 ![alt](本地路径.png) 引用, 会被转成 base64 data URI 内嵌,
  使报告页自包含, 手机离线也能看。
"""
import re
import sys
import os
import html
import base64
import mimetypes
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
REPORTS_DIR = ROOT / "reports"
INDEX_PATH = ROOT / "index.html"

STYLE = """
:root {
  --bg: #0a0e17; --surface: #111726; --surface-2: #1a2233; --border: #232d42;
  --text: #e6eaf2; --muted: #8a94ab; --accent: #4f8cff; --green: #38d996;
  --red: #ff5c6c; --amber: #ffb84d; --purple: #a78bfa;
  --radius: 14px;
  --mono: "SF Mono","JetBrains Mono",Menlo,Consolas,monospace;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif; line-height:1.7; -webkit-font-smoothing:antialiased; }
.wrap { max-width:860px; margin:0 auto; padding:0 24px; }
a { color:var(--accent); text-decoration:none; }
a:hover { text-decoration:underline; }
header { padding:56px 0 32px; border-bottom:1px solid var(--border); background:radial-gradient(1200px 400px at 20% -10%,rgba(79,140,255,.15),transparent 60%),radial-gradient(800px 300px at 90% -20%,rgba(56,217,150,.08),transparent 60%); }
.kicker { display:inline-flex; align-items:center; gap:8px; font-family:var(--mono); font-size:12px; letter-spacing:2px; color:var(--green); text-transform:uppercase; margin-bottom:16px; }
.kicker::before { content:""; width:28px; height:1px; background:var(--green); }
h1 { font-size:clamp(26px,4.5vw,38px); font-weight:700; letter-spacing:-0.02em; line-height:1.2; margin-bottom:10px; }
h1 a { color:var(--text); }
.date { font-family:var(--mono); color:var(--muted); font-size:14px; }
h2 { font-size:20px; font-weight:700; margin:28px 0 14px; letter-spacing:-0.01em; color:var(--text); }
h3 { font-size:17px; font-weight:600; margin:20px 0 10px; color:var(--text); }
p { margin-bottom:12px; }
strong { color:var(--text); font-weight:600; }
em { color:var(--amber); font-style:normal; }
blockquote { border-left:3px solid var(--green); padding:8px 18px; margin:14px 0; background:rgba(56,217,150,.05); border-radius:0 8px 8px 0; }
blockquote p { margin:0; }
code { font-family:var(--mono); color:var(--purple); font-size:13px; background:rgba(167,139,250,.1); padding:1px 7px; border-radius:5px; }
ul,ol { padding-left:24px; margin:12px 0; }
li { margin-bottom:8px; }
img { max-width:100%; border-radius:10px; border:1px solid var(--border); display:block; margin:16px 0; }
table { width:100%; border-collapse:collapse; margin:16px 0; font-size:14px; }
th { text-align:left; font-family:var(--mono); font-size:11px; letter-spacing:1px; text-transform:uppercase; color:var(--muted); padding:10px 12px; border-bottom:1px solid var(--border); }
td { padding:12px; border-bottom:1px solid var(--border); vertical-align:top; }
tr:last-child td { border-bottom:none; }
td:first-child { font-weight:600; color:var(--accent); white-space:nowrap; }
hr { border:none; border-top:1px solid var(--border); margin:28px 0; }
footer { padding:40px 0 64px; text-align:center; color:var(--muted); font-size:13px; }
.back { display:inline-block; margin-top:12px; font-family:var(--mono); font-size:13px; }
.section { padding:12px 0; }
@media (max-width:600px){ .wrap{padding:0 18px;} header{padding:40px 0 24px;} td:first-child{white-space:normal;} }
"""

import markdown


def _embed_image(match):
    """将 ![alt](path) 的本地图片路径转为 base64 data URI."""
    alt, path = match.group(1), match.group(2).strip()
    # 允许从 review.md 所在目录相对解析, 或绝对路径
    p = Path(path)
    if not p.exists():
        # 尝试相对 report md 的目录
        p = Path(_md_dir) / path
    if not p.exists():
        return f'<img alt="{html.escape(alt)}" src="{html.escape(path)}">'
    mime = mimetypes.guess_type(str(p))[0] or "image/png"
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f'<img alt="{html.escape(alt)}" src="data:{mime};base64,{b64}">'


_md_dir = ""


def render_report_md_to_html(md_text: str, md_path: Path) -> str:
    """渲染 markdown, 并把本地图片内嵌为 base64."""
    global _md_dir
    _md_dir = str(md_path.parent)
    # 图片标签: 优先匹配带可选引号/空格的 ![](...)
    img_pat = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    md_text = img_pat.sub(_embed_image, md_text)
    return markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists"],
    )


def build_report_page(date_label: str, body_html: str) -> str:
    title = f"HYPE 价格复盘 · {date_label}"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>{STYLE}</style>
</head>
<body>
<header><div class="wrap">
  <div class="kicker">HYPE Daily Review · ktzwei.github.io/hype-review-blog</div>
  <h1><a href="../">{title}</a></h1>
  <div class="date">{date_label}</div>
</div></header>
<div class="wrap">
{body_html}
<a class="back" href="../">← 返回目录</a>
</div>
<footer><div>仅供学习参考，不构成投资建议 · HYPE-USDT-SWAP 15m</div></footer>
</body></html>
"""


def build_index_page(entries: list[tuple[str, str]]) -> str:
    rows = ""
    for label, href in entries:
        rows += f'<li><a href="{href}"><span class="d">{label}</span></a></li>\n'
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>HYPE 价格复盘 · 归档</title>
<style>{STYLE}
.list {{ list-style:none; padding:0; }}
.list li {{ padding:14px 0; border-bottom:1px dashed var(--border); }}
.list a {{ font-size:17px; font-weight:600; }}
.list .d {{ font-family:var(--mono); color:var(--muted); font-size:14px; margin-right:10px; }}
.count {{ color:var(--muted); font-size:14px; }}
</style>
</head>
<body>
<header><div class="wrap">
  <div class="kicker">HYPE Daily Review</div>
  <h1>HYPE 价格复盘</h1>
  <div class="date">共 {len(entries)} 期 · 每日复盘</div>
</div></header>
<div class="wrap">
  <div class="section">
    <h2>📚 历史复盘</h2>
    <p class="count">点击任意日期查看当天完整复盘（含 K 线图）</p>
    <ul class="list">
{rows}    </ul>
  </div>
</div>
<footer><div>仅供学习参考，不构成投资建议 · HYPE-USDT-SWAP 15m · Brooks 价格行为学</div></footer>
</body></html>
"""


def normalize_date(label: str) -> str:
    m = re.search(r"(\d{4})[.\-](\d{1,2})[.\-](\d{1,2})", label)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return label.replace(".", "-")


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: publish.py <report.md> <date_label> [--push]")
        return 1
    md_path = Path(sys.argv[1])
    date_label = sys.argv[2] if len(sys.argv) > 2 else ""
    do_push = "--push" in sys.argv

    if not md_path.exists():
        print(f"找不到报告文件: {md_path}")
        return 1

    md_text = md_path.read_text(encoding="utf-8")
    body_html = render_report_md_to_html(md_text, md_path)
    REPORTS_DIR.mkdir(exist_ok=True)

    date_slug = normalize_date(date_label) if date_label else datetime.now().strftime("%Y-%m-%d")
    report_path = REPORTS_DIR / f"{date_slug}.html"
    report_path.write_text(build_report_page(date_label or date_slug, body_html), encoding="utf-8")
    print(f"生成报告页: {report_path}")

    entries = []
    for p in sorted(REPORTS_DIR.glob("*.html"), reverse=True):
        label = p.stem.replace("-", ".")
        entries.append((label, f"reports/{p.name}"))
    INDEX_PATH.write_text(build_index_page(entries), encoding="utf-8")
    print(f"更新目录: {INDEX_PATH} ({len(entries)} 期)")

    if do_push:
        os.chdir(ROOT)
        os.system("git add -A && git commit -q -m '新增HYPE复盘' || true")
        os.system("git push -q origin main")
        print("已 push 到 GitHub Pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
