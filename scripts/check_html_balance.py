"""Check HTML div balance (outside <script> tags)"""
import re, sys
path = "app/web/templates/workspace/studio.html"
with open(path, "r", encoding="utf-8") as f:
    html = f.read()

# Remove script content
cleaned = re.sub(r"<script>.*?</script>", "", html, flags=re.DOTALL)
opens = len(re.findall(r"<div[\s>]", cleaned))
closes = len(re.findall(r"</div>", cleaned))

if opens == closes:
    print(f"OK: <div> opens={opens}, closes={closes}, balanced")
    sys.exit(0)
else:
    print(f"FAIL: <div> opens={opens}, closes={closes}, diff={opens-closes}")
    sys.exit(1)
