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
    
    # Filter for blogs that mention this state's name
    related_blogs = [
        post for post in blogs 
        if state['name'].lower() in post['title'].lower() 
        or state['name'].lower() in post['content'].lower()
    ]
    
    # Fallback to general guides if no state-specific match
    if not related_blogs:
        related_blogs = blogs[:3]

    return render_template(
        'state_calculator.html', 
        state=state, 
        states=STATES, 
        related_blogs=related_blogs[:3]
    )

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

@app.route('/compare')
def compare():
    # Get slugs from the URL query params: /compare?states=texas,california,new-york
    slugs = request.args.get('states', '').split(',')
    # Find matching states in your data
    selected_states = [s for s in STATES if s['slug'] in slugs]
    
    return render_template('compare.html', selected_states=selected_states)

@app.route('/compare/<state1>-vs-<state2>')
def compare_specific(state1, state2):
    # Logic to fetch both states and redirect/render the compare page
    return render_template('compare.html', selected_states=[s for s in STATES if s['slug'] in [state1, state2]])

@app.route('/sitemap.xml')
def sitemap():
    # Use your actual production domain for SEO
    domain = "https://statestaxcalc.com"
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    # 1. Add Homepage
    xml += f'  <url><loc>{domain}/</loc><priority>1.0</priority></url>\n'
    
    # 2. Add All-Calculators Directory
    xml += f'  <url><loc>{domain}/all-calculators</loc><priority>0.9</priority></url>\n'
    
    # 3. Add Blog Index
    xml += f'  <url><loc>{domain}/blog</loc><priority>0.9</priority></url>\n'

    # Add this inside the sitemap() route in app.py
    xml += f'  <url><loc>{domain}/compare</loc><priority>0.9</priority></url>\n'
    
    # 4. Add State Calculator Pages
    for s in STATES:
        xml += f'  <url><loc>{domain}/tax-calculator/{s["slug"]}</loc><priority>0.8</priority></url>\n'
    
    # 5. Add All Blog Posts
    for post in blogs:
        xml += f'  <url><loc>{domain}/blog/{post["slug"]}</loc><priority>0.7</priority></url>\n'
        
    xml += '</urlset>'
    return xml, 200, {'Content-Type': 'application/xml'}

if __name__ == '__main__':
    app.run(debug=True)