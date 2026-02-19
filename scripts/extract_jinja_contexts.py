#!/usr/bin/env python3
import ast
import os
import json

ROOT = os.path.join(os.path.dirname(__file__), '..')

results = {}

def record(template, names, src):
    if not template:
        template = '<dynamic>'
    d = results.setdefault(template, {'vars': set(), 'locations': set()})
    d['vars'].update(names)
    d['locations'].add(src)

class CallVisitor(ast.NodeVisitor):
    def __init__(self, path):
        self.path = path

    def visit_Call(self, node):
        # func can be attribute or name
        name = None
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr

        if name in ('render_title_template', 'render_template'):
            # template name: first positional arg if constant
            template = None
            if node.args:
                arg0 = node.args[0]
                if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                    template = arg0.value
            # collect explicit keyword arg names
            kw_names = [kw.arg for kw in node.keywords if kw.arg]
            record(template, kw_names, f"{self.path}:{node.lineno}")

        self.generic_visit(node)


for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, 'cps')):
    # skip compiled/venv folders
    for fn in filenames:
        if not fn.endswith('.py'):
            continue
        path = os.path.join(dirpath, fn)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                src = f.read()
            tree = ast.parse(src, filename=path)
            CallVisitor(path).visit(tree)
        except Exception as e:
            print(f"Failed to parse {path}: {e}")

# convert sets to lists for JSON
out = {tpl: {'vars': sorted(list(data['vars'])), 'locations': sorted(list(data['locations']))} for tpl, data in results.items()}
print(json.dumps(out, indent=2))
