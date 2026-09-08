import sys
content = open('dashboard.py', 'r', encoding='utf-8').read()
replacements = {
    'âœˆï¸': '✈️',
    'â€”': '—',
    'ðŸ—ºï¸': '🗺️',
    'â†’': '→',
    'â‚¹': '₹',
    'ðŸ’°': '💰',
    'ðŸ“Š': '📊',
    'ðŸ“¦': '📦',
    'ðŸ“…': '📅',
    'ðŸ †': '🏆',
    'ðŸ§®': '🧮',
    'ðŸ“ ': '📌',
    'ðŸ”´': '🔴',
    'ðŸŸ¢': '🟢',
    'âšª': '⚪',
    'ðŸ‡®ðŸ‡³': '🇮🇳',
    'ðŸ ›ï¸': '🏛️',
    'âœ…': '✅'
}
for k, v in replacements.items():
    content = content.replace(k, v)
with open('dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')
