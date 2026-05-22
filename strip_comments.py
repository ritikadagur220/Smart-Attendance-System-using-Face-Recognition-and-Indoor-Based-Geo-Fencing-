import os
import re

def strip_comments_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    ext = os.path.splitext(filepath)[1].lower()

    if ext in ['.py']:
        # Strip python # comments, but avoid touching strings if possible
        # A simple multi-line replace for python (careful with # in strings though)
        content = re.sub(r'(?m)^\s*#.*$', '', content)
        content = re.sub(r'(?m)\s+#.*$', '', content)
        
    elif ext in ['.js', '.kt', '.java']:
        # Strip // comments
        content = re.sub(r'(?m)^\s*//.*$', '', content)
        content = re.sub(r'(?m)\s+//.*$', '', content)
        # Strip /* */ comments
        content = re.sub(r'/\*[\s\S]*?\*/', '', content)

    elif ext in ['.css']:
        content = re.sub(r'/\*[\s\S]*?\*/', '', content)
        
    elif ext in ['.html', '.xml']:
        # Strip <!-- --> comments
        content = re.sub(r'<!--[\s\S]*?-->', '', content)

    # Clean up excessive blank lines left over
    content = re.sub(r'\n{3,}', '\n\n', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def process_dir(directory):
    for root, dirs, files in os.walk(directory):
        if 'venv' in root or '.git' in root or 'node_modules' in root:
            continue
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in ['.py', '.js', '.css', '.html', '.kt', '.java', '.xml']:
                if file != "strip_comments.py":
                    filepath = os.path.join(root, file)
                    strip_comments_from_file(filepath)
                    print(f"Stripped comments from {filepath}")

if __name__ == '__main__':
    base_dir = r"c:\Users\ritik\Desktop\final year project"
    process_dir(base_dir)
