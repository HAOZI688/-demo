"""Extract studio.html inline JS for node --check"""
import re
import sys
path = "app/web/templates/workspace/studio.html"
with open(path, "r", encoding="utf-8") as f:
    html = f.read()
m = re.search(r"<script>\s*\n(.*?)</script>\s*</body>", html, re.DOTALL)
if m:
    sys.stdout.write(m.group(1))
else:
    sys.exit(1)
