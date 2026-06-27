import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sdev.settings')
django.setup()

from django.template.loader import get_template
from django.template.exceptions import TemplateDoesNotExist
from django.template import TemplateSyntaxError

template_dir = r"c:\Users\user\Desktop\merged_project\main\templates"
errors = []

for root, dirs, files in os.walk(template_dir):
    for f in files:
        if f.endswith('.html'):
            rel_dir = os.path.relpath(root, template_dir)
            if rel_dir == '.':
                template_name = f
            else:
                template_name = os.path.join(rel_dir, f).replace('\\', '/')
            try:
                get_template(template_name)
            except TemplateSyntaxError as e:
                errors.append(f"Syntax Error in {template_name}: {e}")
            except TemplateDoesNotExist as e:
                errors.append(f"Not Found Error in {template_name}: {e}")
            except Exception as e:
                errors.append(f"Error in {template_name}: {e}")

with open("errors_utf8.txt", "w", encoding="utf-8") as f:
    if errors:
        f.write("Found errors in templates:\n")
        for e in errors:
            f.write(e + "\n")
    else:
        f.write("All templates compiled successfully without syntax errors.")
