import sys
content = open('dashboard.py', 'r', encoding='utf-8').read()
replacements = {
    'â€“': '-',
    'â”€': '─',
    'â€˜': '\'',
    'â€™': '\'',
    'â€œ': '\"',
    'â€ ': '\"'
}
for k, v in replacements.items():
    content = content.replace(k, v)
with open('dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done fixing remaining mojibake!')
