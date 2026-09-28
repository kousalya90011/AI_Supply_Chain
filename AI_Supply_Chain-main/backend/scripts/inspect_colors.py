from pathlib import Path
import re

css_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "App.css"
content = css_path.read_text(encoding="utf-8")

hex_matches = re.findall(r'#([0-9a-fA-F]{3,8})\b', content)
from collections import Counter
counts = Counter([h.lower() for h in hex_matches])

print("Top 25 Hex Colors in App.css:")
for color, count in counts.most_common(25):
    print(f"  #{color:8s}: {count}")

rgb_matches = re.findall(r'rgba?\([^\)]+\)', content)
rgb_counts = Counter(rgb_matches)
print("\nTop 15 RGBA Colors in App.css:")
for color, count in rgb_counts.most_common(15):
    print(f"  {color:35s}: {count}")
