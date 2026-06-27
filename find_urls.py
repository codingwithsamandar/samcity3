import os
import re

template_dir = r"c:\Users\user\Desktop\merged_project\main\templates"
urls = set()

for root, dirs, files in os.walk(template_dir):
    for f in files:
        if f.endswith('.html'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
                matches = re.findall(r'(?:href|action)="/([^"]*)"', content)
                for m in matches:
                    urls.add("/" + m)

with open(r"c:\Users\user\Desktop\merged_project\urls.txt", "w", encoding="utf-8") as f:
    f.write("Found URLs:\n")
    for u in sorted(urls):
        f.write(u + "\n")
