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

# UPDATED: 2026 Federal brackets (single, married_joint, head_of_household)
# Data based on official 2026 inflation adjustments
FEDERAL_BRACKETS = {
    'single': [
        (0, 12400, 0.10), (12401, 50400, 0.12), (50401, 105700, 0.22), 
        (105701, 201775, 0.24), (201776, 256225, 0.32), (256226, 640600, 0.35), 
        (640601, float('inf'), 0.37)
    ],
    'married': [
        (0, 24800, 0.10), (24801, 100800, 0.12), (100801, 211400, 0.22), 
        (211401, 403550, 0.24), (403551, 512450, 0.32), (512451, 768700, 0.35), 
        (768701, float('inf'), 0.37)
    ],
    'hoh': [
        (0, 17700, 0.10), (17701, 67450, 0.12), (67451, 105700, 0.22), 
        (105701, 201750, 0.24), (201751, 256200, 0.32), (256201, 640600, 0.35), 
        (640601, float('inf'), 0.37)
    ]
}

def calculate_tax(income, brackets):
    if not brackets:
        return 0.0
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
    income = float(data.get('income', 0))
    filing = data.get('filing_status', 'single')
    state_slug = data.get('state_slug')
    is_1099 = data.get('is_1099', False)  # New 1099 toggle check

    state = next((s for s in STATES if s['slug'] == state_slug), None)
    
    # Standard Federal Income Tax
    fed_tax = calculate_tax(income, FEDERAL_BRACKETS.get(filing, FEDERAL_BRACKETS['single']))

    # NEW: Add Self-Employment Tax (15.3%) if 1099 mode is active
    se_tax = 0.0
    if is_1099:
        # SE tax is calculated on 92.35% of net earnings
        taxable_se_income = income * 0.9235
        # 15.3% combined rate
        se_tax = taxable_se_income * 0.153
        # Note: In a real tax return, half of SE tax is deductible from income, 
        # but for a quick estimator, adding the 15.3% is the most helpful for users.

    # State Tax
    state_tax = 0.0
    if state and state.get('has_income_tax'):
        brackets = state.get('brackets', {}).get(filing, [])
        state_tax = calculate_tax(income, brackets)

    total_tax = fed_tax + state_tax + se_tax
    effective = (total_tax / income * 100) if income > 0 else 0

    return jsonify({
        'federal_tax': round(fed_tax + se_tax, 2), # Combined for the chart simplicity
        'se_tax_only': round(se_tax, 2),           # Sent separately if you want to show it
        'state_tax': round(state_tax, 2),
        'total_tax': round(total_tax, 2),
        'effective_rate': round(effective, 2),
        'take_home': round(income - total_tax, 2)
    })

@app.route('/blog')
def blog_index():
    return render_template('blog_index.html', blogs=blogs)


@app.route('/all-calculators')
def all_calculators():
    # Sort states alphabetically for the directory page
    sorted_states = sorted(STATES, key=lambda x: x['name'])
    return render_template('all_calculators.html', states=sorted_states)

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
                           blogs=blogs)

@app.route('/sitemap.xml')
def sitemap():
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    # Change domain to your actual production domain for SEO
    domain = "https://statestaxcalc.com" 
    xml += f'<url><loc>{domain}/</loc></url>\n'
    for s in STATES:
        xml += f'<url><loc>{domain}/tax-calculator/{s["slug"]}</loc></url>\n'
    xml += '</urlset>'
    return xml, 200, {'Content-Type': 'application/xml'}

if __name__ == '__main__':
    app.run(debug=True)