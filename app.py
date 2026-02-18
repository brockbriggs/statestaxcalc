from flask import Flask, render_template, request, jsonify, abort
import json
from config import SECRET_KEY
import markdown
from data.blog_posts import blogs
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

with open('data/states.json') as f:
    STATES = json.load(f)['states']

# 2025 Federal brackets (single, married_joint, head_of_household)
FEDERAL_BRACKETS = {
    'single': [(0, 11925, 0.10), (11926, 48475, 0.12), (48476, 103350, 0.22), (103351, 197300, 0.24), (197301, 250525, 0.32), (250526, 626350, 0.35), (626351, float('inf'), 0.37)],
    'married': [(0, 23850, 0.10), (23851, 96950, 0.12), (96951, 206700, 0.22), (206701, 394600, 0.24), (394601, 501050, 0.32), (501051, 751600, 0.35), (751601, float('inf'), 0.37)],
    'hoh': [(0, 17000, 0.10), (17001, 64850, 0.12), (64851, 103350, 0.22), (103351, 197300, 0.24), (197301, 250500, 0.32), (250501, 626350, 0.35), (626351, float('inf'), 0.37)]
}

def calculate_tax(income, brackets):
    tax = 0.0
    prev = 0.0
    for low, high, rate in brackets:
        if income > high:
            tax += (high - prev) * rate
            prev = high
        else:
            tax += (income - prev) * rate
            return round(tax, 2)
    return round(tax, 2)

@app.route('/')
def home():
    return render_template('index.html', states=STATES)

@app.route('/tax-calculator/<slug>')
def state_page(slug):
    state = next((s for s in STATES if s['slug'] == slug), None)
    if not state:
        abort(404)
    return render_template('state_calculator.html', state=state, states=STATES)

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.get_json()
    income = float(data['income'])
    filing = data['filing_status']
    state_slug = data['state_slug']

    state = next((s for s in STATES if s['slug'] == state_slug), None)
    fed_tax = calculate_tax(income, FEDERAL_BRACKETS.get(filing, FEDERAL_BRACKETS['single']))

    # State tax – full progressive if data provided, else 0 (extend brackets in states.json)
    state_tax = 0.0
    if state and state.get('has_income_tax') and 'brackets' in state:
        state_tax = calculate_tax(income, state['brackets'].get(filing, []))
    elif state and not state.get('has_income_tax'):
        state_tax = 0.0

    total_tax = fed_tax + state_tax
    effective = (total_tax / income * 100) if income > 0 else 0

    return jsonify({
        'federal_tax': fed_tax,
        'state_tax': round(state_tax, 2),
        'total_tax': round(total_tax, 2),
        'effective_rate': round(effective, 2),
        'take_home': round(income - total_tax, 2)
    })

@app.route('/blog')
def blog_index():
    return render_template('blog_index.html', blogs=blogs)

@app.route('/blog/<slug>')
def blog_post(slug):
    post = next((p for p in blogs if p['slug'] == slug), None)
    if not post:
        abort(404)
    
    html_content = markdown.markdown(post['content'], extensions=['tables', 'fenced_code'])
    
    try:
        nice_date = datetime.strptime(post['date'], '%Y-%m-%d').strftime('%B %d, %Y')
    except:
        nice_date = post['date']
    
    return render_template('blog_post.html', 
                           post=post, 
                           content=html_content,
                           nice_date=nice_date,
                           blogs=blogs)   # ← This line fixes the error

@app.route('/sitemap.xml')
def sitemap():
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += '<url><loc>https://yourdomain.com/</loc></url>\n'
    for s in STATES:
        xml += f'<url><loc>https://yourdomain.com/tax-calculator/{s["slug"]}</loc></url>\n'
    xml += '</urlset>'
    return xml, 200, {'Content-Type': 'application/xml'}

if __name__ == '__main__':
    app.run(debug=True)