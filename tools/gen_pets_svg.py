"""参数化批量生成宠物 SVG：数量不限，全部来自 config/pets.json。

用法：
  python tools/gen_pets_svg.py            # 生成目录中全部物种 x 3 形态
  python tools/gen_pets_svg.py --key 鹿蜀的 svg_key   # 只重生成一种
  python tools/gen_pets_svg.py --list     # 查看可生成的 svg_key

输出：pet_system/web/static/pets/*.svg
新增怪兽只需在 config/pets.json 里追加一项并写好 art.features，无需改本文件。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT, "config", "pets.json")
OUT_DIR = os.path.join(ROOT, "pet_system", "web", "static", "pets")

HEAD = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240" width="240" height="240">\n<title>{title}</title>\n'
TAIL = "\n</svg>\n"

# 身体后方的装饰（尾巴/翅膀/壳等）
BACK = {
    "flame": '<path d="M170 150 q46 -6 40 -46 q-4 -22 -24 -30 q14 24 -4 40 q-8 8 -20 8 z" fill="{edge}" opacity=".9"/>',
    "tails": (
        '<g fill="{body}" stroke="{edge}" stroke-width="2" opacity=".95">'
        '<path d="M172 170 q46 -4 42 -44 q-2 -20 -20 -28 q12 24 -6 36 q-10 6 -20 4 z"/>'
        '<path d="M170 154 q44 -20 34 -56 q-6 -18 -24 -20 q16 22 0 38 q-8 8 -18 8 z"/>'
        '<path d="M166 140 q34 -34 18 -64 q-10 -14 -26 -12 q20 20 6 42 q-8 12 -16 16 z"/>'
        '</g>'
    ),
    "wings": (
        '<path d="M62 132 Q12 96 28 52 Q46 80 76 92 z" fill="{body}" stroke="{edge}" stroke-width="2.5"/>'
        '<path d="M178 132 Q228 96 212 52 Q194 80 164 92 z" fill="{body}" stroke="{edge}" stroke-width="2.5"/>'
    ),
    "fin": (
        '<path d="M76 132 q44 -32 88 0 q-44 -16 -88 0 z" fill="{accent}" opacity=".9"/>'
        '<path d="M178 170 q34 -8 30 -38 q-4 -16 -18 -20 q10 22 -4 34 q-8 6 -16 6 z" fill="{body}" stroke="{edge}" stroke-width="2"/>'
    ),
    "shell": (
        '<ellipse cx="120" cy="166" rx="64" ry="50" fill="{edge}" opacity=".35" stroke="{edge}" stroke-width="3"/>'
        '<g fill="none" stroke="{edge}" stroke-width="2" opacity=".6">'
        '<path d="M120 118 v96 M58 166 h124 M76 138 l88 56 M164 138 l-88 56"/></g>'
    ),
    "feathers": (
        '<g fill="{accent}" stroke="{edge}" stroke-width="1.5" opacity=".9">'
        '<path d="M170 174 q36 -6 34 -36 q-4 -14 -16 -18 q8 24 -8 34 q-8 4 -14 4 z"/>'
        '<path d="M166 162 q30 -22 20 -50 q-8 -12 -20 -10 q16 24 4 44 q-6 8 -12 10 z"/>'
        '</g>'
    ),
    "ripple": (
        '<g fill="none" stroke="{accent}" stroke-width="3" stroke-linecap="round" opacity=".85">'
        '<path d="M158 196 q18 8 36 0"/><path d="M166 208 q14 6 28 0"/></g>'
    ),
    "mane": (
        '<g fill="{edge}" opacity=".75">'
        '<path d="M80 112 q-20 -34 2 -54 q2 26 24 40 z"/>'
        '<path d="M120 100 q-8 -40 14 -54 q-6 30 10 50 z"/>'
        '<path d="M150 108 q14 -36 36 -38 q-18 24 -12 48 z"/></g>'
    ),
}

# 身体前方的装饰（耳朵/角/喙/花纹等）
FRONT = {
    "cloud_ears": (
        '<circle cx="86" cy="112" r="30" fill="{body}" stroke="{edge}" stroke-width="2.5"/>'
        '<circle cx="120" cy="98" r="36" fill="{body}" stroke="{edge}" stroke-width="2.5"/>'
        '<circle cx="154" cy="112" r="30" fill="{body}" stroke="{edge}" stroke-width="2.5"/>'
    ),
    "pointy_ears": (
        '<path d="M70 104 L60 52 L104 82 z" fill="{body}" stroke="{edge}" stroke-width="2.5" stroke-linejoin="round"/>'
        '<path d="M160 104 L170 52 L126 82 z" fill="{body}" stroke="{edge}" stroke-width="2.5" stroke-linejoin="round"/>'
    ),
    "leaf_ears": (
        '<ellipse cx="86" cy="92" rx="12" ry="18" fill="{body}" stroke="{edge}" stroke-width="2" transform="rotate(-30 86 92)"/>'
        '<ellipse cx="154" cy="92" rx="12" ry="18" fill="{body}" stroke="{edge}" stroke-width="2" transform="rotate(30 154 92)"/>'
    ),
    "antlers": (
        '<g stroke="{edge}" stroke-width="4" stroke-linecap="round" fill="none">'
        '<path d="M88 78 L74 44 M74 44 L60 34 M74 44 L82 30"/>'
        '<path d="M152 78 L166 44 M166 44 L180 34 M166 44 L158 30"/></g>'
    ),
    "horn": (
        '<path d="M88 70 L78 34 L108 60 z" fill="{accent}" stroke="{edge}" stroke-width="2" stroke-linejoin="round"/>'
        '<path d="M144 70 L154 34 L124 60 z" fill="{accent}" stroke="{edge}" stroke-width="2" stroke-linejoin="round"/>'
    ),
    "beak": '<path d="M120 156 l15 9 -15 9 z" fill="{accent}" stroke="{edge}" stroke-width="2" stroke-linejoin="round"/>',
    "sparkle": '<path d="M120 64 l4 9 9 4 -9 4 -4 9 -4 -9 -9 -4 9 -4 z" fill="{accent}"/>',
    "stars": (
        '<path d="M62 50 l3 7 7 3 -7 3 -3 7 -3 -7 -7 -3 7 -3 z" fill="{accent}"/>'
        '<path d="M180 44 l3 7 7 3 -7 3 -3 7 -3 -7 -7 -3 7 -3 z" fill="{accent}"/>'
    ),
    "stripes": (
        '<g stroke="{accent}" stroke-width="4" stroke-linecap="round" opacity=".75" fill="none">'
        '<path d="M78 142 l12 8 M76 166 l12 6 M150 142 l-12 8 M152 166 l-12 6"/></g>'
    ),
    "book": (
        '<g><rect x="96" y="176" width="48" height="30" rx="5" fill="#FFFFFF" stroke="{edge}" stroke-width="2"/>'
        '<path d="M120 176 v30" stroke="{edge}" stroke-width="2"/><path d="M104 185 h10 M126 185 h10" stroke="{edge}" stroke-width="2" stroke-linecap="round"/></g>'
    ),
    "spout": (
        '<g fill="{accent}" opacity=".9"><circle cx="120" cy="70" r="6"/>'
        '<circle cx="108" cy="56" r="4"/><circle cx="132" cy="54" r="5"/></g>'
    ),
}


def load_catalog():
    with open(CATALOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def pieces(items, table, art):
    # 同一个特征列表会分别喂给 BACK / FRONT，只取当前层认识的那部分
    out = []
    for key in items:
        if key in table:
            out.append(table[key].format(**art))
    return "".join(out)


def eyes(art):
    return (f'<ellipse cx="97" cy="140" rx="9" ry="11" fill="{art["eye"]}"/>'
            f'<ellipse cx="143" cy="140" rx="9" ry="11" fill="{art["eye"]}"/>'
            '<circle cx="100" cy="136" r="3" fill="#FFFFFF"/>'
            '<circle cx="146" cy="136" r="3" fill="#FFFFFF"/>')


def face(art, has_beak=False):
    mouth = "" if has_beak else (
        f'<path d="M112 158 q8 9 16 0" fill="none" stroke="{art["eye"]}" stroke-width="2.5" stroke-linecap="round"/>'
    )
    return (f'<ellipse cx="78" cy="158" rx="9" ry="5" fill="{art["blush"]}" opacity="0.55"/>'
            f'<ellipse cx="162" cy="158" rx="9" ry="5" fill="{art["blush"]}" opacity="0.55"/>'
            + mouth)


def feet(art):
    return (f'<ellipse cx="96" cy="206" rx="15" ry="8" fill="{art["belly"]}"/>'
            f'<ellipse cx="144" cy="206" rx="15" ry="8" fill="{art["belly"]}"/>')


def render_egg(cn, art):
    svg = HEAD.format(title=cn + "蛋")
    svg += (f'<ellipse cx="120" cy="134" rx="70" ry="84" fill="{art["body"]}" stroke="{art["edge"]}" stroke-width="3"/>'
            '<circle cx="96" cy="96" r="19" fill="#FFFFFF" opacity=".85"/>'
            '<circle cx="118" cy="88" r="24" fill="#FFFFFF" opacity=".85"/>'
            '<circle cx="140" cy="98" r="17" fill="#FFFFFF" opacity=".85"/>'
            f'<path d="M104 72 L116 84 L107 93 L121 101" fill="none" stroke="{art["edge"]}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="M166 78 l3 7 7 3 -7 3 -3 7 -3 -7 -7 -3 7 -3 z" fill="{art["accent"]}"/>')
    return svg + TAIL


def render_juvenile(cn, art):
    features = art.get("features") or []
    svg = HEAD.format(title=cn + "幼体")
    svg += pieces(features, BACK, art)
    svg += f'<ellipse cx="120" cy="152" rx="60" ry="56" fill="{art["body"]}" stroke="{art["edge"]}" stroke-width="2.5"/>'
    svg += pieces(features, FRONT, art)
    svg += eyes(art) + face(art, "beak" in features) + feet(art)
    return svg + TAIL


def render_adult(cn, art):
    features = art.get("features") or []
    svg = HEAD.format(title=cn + "成体")
    svg += pieces(features, BACK, art)
    svg += f'<ellipse cx="120" cy="152" rx="68" ry="60" fill="{art["body"]}" stroke="{art["edge"]}" stroke-width="2.5"/>'
    svg += f'<ellipse cx="120" cy="170" rx="40" ry="34" fill="{art["belly"]}"/>'
    svg += pieces(features, FRONT, art)
    svg += eyes(art) + face(art, "beak" in features) + feet(art)
    return svg + TAIL


def main():
    items = load_catalog()
    only = None
    if "--key" in sys.argv:
        only = sys.argv[sys.argv.index("--key") + 1]
    if "--list" in sys.argv:
        for x in items:
            print(x["svg_key"], x["name"])
        return
    known = set(BACK) | set(FRONT)
    for x in items:
        unknown = [f for f in x["art"].get("features", []) if f not in known]
        if unknown:
            raise ValueError(f"{x['name']} 的 art.features 含未知项：{unknown}")
    os.makedirs(OUT_DIR, exist_ok=True)
    count = 0
    for x in items:
        if only and x["svg_key"] != only:
            continue
        art = x["art"]
        for form, fn in (("egg", render_egg), ("juvenile", render_juvenile), ("adult", render_adult)):
            path = os.path.join(OUT_DIR, f"{x['svg_key']}_{form}.svg")
            with open(path, "w", encoding="utf-8") as f:
                f.write(fn(x["name"], art))
            count += 1
            print("written:", os.path.basename(path))
    print(f"done: {count} svg -> {OUT_DIR}")


if __name__ == "__main__":
    main()
