"""参数化批量生成 5 阶 x 3 形态 = 15 个 SVG 宠物图形。

用法：python tools/gen_pets_svg.py
输出：pet_system/web/static/pets/*.svg

改风格只需改 TIERS 里的颜色/装饰，或用 --key 只重生成某一阶。
"""
import os
import sys

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "pet_system", "web", "static", "pets")

# 每阶一个主色板 + 专属装饰片段（蛋期共用模板，只换颜色）
TIERS = [
    dict(key="cloud_beast", cn="云团兽", body="#FFFFFF", edge="#D6E7F5",
         belly="#E8F3FC", eye="#3A3A4A", blush="#FFB3C1",
         crown='<path d="M120 70 l4 9 9 4 -9 4 -4 9 -4 -9 -9 -4 9 -4 z" fill="#FFD966"/>',
         ears='<circle cx="86" cy="112" r="30" fill="{body}" stroke="{edge}" stroke-width="2.5"/><circle cx="120" cy="98" r="36" fill="{body}" stroke="{edge}" stroke-width="2.5"/><circle cx="154" cy="112" r="30" fill="{body}" stroke="{edge}" stroke-width="2.5"/>',
         extra=""),
    dict(key="ember_fox", cn="火苗狐", body="#FF9A52", edge="#E8762E",
         belly="#FFE0B2", eye="#3A2A24", blush="#FF6B6B",
         crown="",
         ears='<path d="M70 104 L60 52 L104 82 z" fill="{body}" stroke="{edge}" stroke-width="2.5" stroke-linejoin="round"/><path d="M160 104 L170 52 L126 82 z" fill="{body}" stroke="{edge}" stroke-width="2.5" stroke-linejoin="round"/>',
         extra='<path d="M170 150 q46 -6 40 -46 q-4 -22 -24 -30 q14 24 -4 40 q-8 8 -20 8 z" fill="#FF8C42" stroke="#E8762E" stroke-width="2"/>'),
    dict(key="star_deer", cn="星角鹿", body="#B4A5EC", edge="#8E7BD6",
         belly="#E8E2FA", eye="#3A2A4A", blush="#FF9EC4",
         crown='<path d="M60 34 l3 6 6 3 -6 3 -3 6 -3 -6 -6 -3 6 -3 z" fill="#FFD966"/><path d="M180 34 l3 6 6 3 -6 3 -3 6 -3 -6 -6 -3 6 -3 z" fill="#FFD966"/>',
         ears='<ellipse cx="86" cy="92" rx="12" ry="18" fill="{body}" transform="rotate(-30 86 92)"/><ellipse cx="154" cy="92" rx="12" ry="18" fill="{body}" transform="rotate(30 154 92)"/>',
         extra='<g stroke="{edge}" stroke-width="4" stroke-linecap="round" fill="none"><path d="M88 78 L74 44 M74 44 L60 34 M74 44 L82 30"/><path d="M152 78 L166 44 M166 44 L180 34 M166 44 L158 30"/></g>'),
    dict(key="mist_whale", cn="海雾鲸", body="#5FC8E8", edge="#2E9CC0",
         belly="#DFF5FB", eye="#2A3A48", blush="#FF9EB5",
         crown="",
         ears='<path d="M74 128 q46 -30 92 0 q-46 -14 -92 0 z" fill="#8FDDEE"/>',
         extra='<path d="M120 90 q-6 -18 4 -30 q-2 16 6 22 q10 -14 6 -30 q14 18 2 38 z" fill="#BFEFFF" opacity="0.9"/>'),
    dict(key="star_dragon", cn="星辰龙", body="#C9A0F0", edge="#9B6FD6",
         belly="#F3E8FB", eye="#3A2A48", blush="#FF9EC4",
         crown='<path d="M116 52 l4 9 9 4 -9 4 -4 9 -4 -9 -9 -4 9 -4 z" fill="#FFD966"/>',
         ears='<path d="M88 70 L78 34 L108 60 z" fill="#FFD166" stroke="#E8B84B" stroke-width="2" stroke-linejoin="round"/><path d="M144 70 L154 34 L124 60 z" fill="#FFD166" stroke="#E8B84B" stroke-width="2" stroke-linejoin="round"/>',
         extra='<path d="M56 128 Q10 90 28 52 Q44 78 74 88 z" fill="#C9A0F0" stroke="#9B6FD6" stroke-width="2.5"/><path d="M184 128 Q230 90 212 52 Q196 78 166 88 z" fill="#C9A0F0" stroke="#9B6FD6" stroke-width="2.5"/>'),
]

HEAD = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240" width="240" height="240">\n<title>{title}</title>\n'
TAIL = "\n</svg>\n"


def eyes(t):
    return (f'<ellipse cx="97" cy="140" rx="9" ry="11" fill="{t["eye"]}"/>'
            f'<ellipse cx="143" cy="140" rx="9" ry="11" fill="{t["eye"]}"/>'
            '<circle cx="100" cy="136" r="3" fill="#FFFFFF"/>'
            '<circle cx="146" cy="136" r="3" fill="#FFFFFF"/>')


def face(t):
    return (f'<ellipse cx="78" cy="158" rx="9" ry="5" fill="{t["blush"]}" opacity="0.55"/>'
            f'<ellipse cx="162" cy="158" rx="9" ry="5" fill="{t["blush"]}" opacity="0.55"/>'
            f'<path d="M112 158 q8 9 16 0" fill="none" stroke="{t["eye"]}" stroke-width="2.5" stroke-linecap="round"/>')


def feet(t):
    return (f'<ellipse cx="96" cy="206" rx="15" ry="8" fill="{t["belly"]}"/>'
            f'<ellipse cx="144" cy="206" rx="15" ry="8" fill="{t["belly"]}"/>')


def render_egg(t):
    b = HEAD.format(title=t["cn"] + "蛋")
    b += (f'<ellipse cx="120" cy="134" rx="70" ry="84" fill="{t["body"]}" stroke="{t["edge"]}" stroke-width="3"/>'
          '<circle cx="96" cy="96" r="19" fill="#FFFFFF"/>'
          '<circle cx="118" cy="88" r="24" fill="#FFFFFF"/>'
          '<circle cx="140" cy="98" r="17" fill="#FFFFFF"/>'
          '<path d="M104 72 L116 84 L107 93 L121 101" fill="none" stroke="{edge}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
          '<path d="M166 78 l3 7 7 3 -7 3 -3 7 -3 -7 -7 -3 7 -3 z" fill="#FFD966"/>').format(
              body=t["body"], edge=t["edge"])
    return b + TAIL


def render_juvenile(t):
    b = HEAD.format(title=t["cn"] + "幼体")
    b += (f'<ellipse cx="120" cy="152" rx="60" ry="56" fill="{t["body"]}" stroke="{t["edge"]}" stroke-width="2.5"/>'
          + t["ears"].format(**t) + eyes(t) + face(t) + feet(t))
    return b + TAIL


def render_adult(t):
    b = HEAD.format(title=t["cn"] + "成体")
    b += (t["extra"].format(**t)
          + f'<ellipse cx="120" cy="152" rx="68" ry="60" fill="{t["body"]}" stroke="{t["edge"]}" stroke-width="2.5"/>'
          + f'<ellipse cx="120" cy="170" rx="40" ry="34" fill="{t["belly"]}"/>'
          + t["ears"].format(**t) + eyes(t) + face(t) + feet(t) + t["crown"].format(**t))
    return b + TAIL


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    only = sys.argv[sys.argv.index("--key") + 1] if "--key" in sys.argv else None
    count = 0
    for t in TIERS:
        if only and t["key"] != only:
            continue
        for form, fn in (("egg", render_egg), ("juvenile", render_juvenile), ("adult", render_adult)):
            path = os.path.join(OUT_DIR, f"{t['key']}_{form}.svg")
            with open(path, "w", encoding="utf-8") as f:
                f.write(fn(t))
            count += 1
            print("written:", os.path.basename(path))
    print(f"done: {count} svg -> {OUT_DIR}")


if __name__ == "__main__":
    main()
