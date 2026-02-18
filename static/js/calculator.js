// static/js/calculator.js - Fixed & robust version for the new dark layout

document.addEventListener('DOMContentLoaded', function () {
    const incomeInput = document.getElementById('income');
    const filingSelect = document.getElementById('filing_status');
    const calculateBtn = document.getElementById('calculateBtn');

    if (!incomeInput || !filingSelect || !calculateBtn) {
        console.error("Calculator elements not found - check IDs");
        return;
    }

    // Allow pressing Enter in the income field
    incomeInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') calculateTaxes();
    });

    calculateBtn.addEventListener('click', calculateTaxes);
});

async function calculateTaxes() {
    const incomeInput = document.getElementById('income');
    const filingSelect = document.getElementById('filing_status');
    const calculateBtn = document.getElementById('calculateBtn');

    const income = parseFloat(incomeInput.value) || 0;
    const filingStatus = filingSelect.value;
    const stateSlug = window.location.pathname.split('/').pop();

    if (income <= 0) {
        alert("Please enter a valid income amount");
        return;
    }

    const originalText = calculateBtn.innerHTML;
    calculateBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Calculating...`;
    calculateBtn.disabled = true;

    try {
        const response = await fetch('/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                income: income,
                filing_status: filingStatus,
                state_slug: stateSlug
            })
        });

        if (!response.ok) throw new Error('Server error');

        const data = await response.json();

        updateResults(data, income);

        // Show results, hide placeholder
        document.getElementById('placeholder').classList.add('d-none');
        document.getElementById('resultsContainer').classList.remove('d-none');

    } catch (err) {
        console.error(err);
        alert("Sorry, something went wrong. Please try again.");
    } finally {
        calculateBtn.innerHTML = originalText;
        calculateBtn.disabled = false;
    }
}

function formatCurrency(amount) {
    return '$' + parseFloat(amount).toLocaleString('en-US');
}

function updateResults(data, income) {
    document.getElementById('takehome').textContent = formatCurrency(data.take_home);
    document.getElementById('federal_tax').textContent = formatCurrency(data.federal_tax);
    document.getElementById('state_tax').textContent = formatCurrency(data.state_tax);

    renderTaxChart(data, income);
}

function renderTaxChart(data, income) {
    const ctx = document.getElementById('taxPieChart');
    if (!ctx) return;

    if (window.taxChart) window.taxChart.destroy();

    const federal = parseFloat(data.federal_tax);
    const stateTax = parseFloat(data.state_tax);
    const takeHome = parseFloat(data.take_home);

    window.taxChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Take-Home Pay', 'Federal Tax', 'State Tax'],
            datasets: [{
                data: [takeHome, federal, stateTax],
                backgroundColor: ['#10b981', '#ef4444', '#f59e0b'],
                borderColor: '#1e2937',
                borderWidth: 6,
            }]
        },
        options: {
            responsive: true,
            cutout: '65%',
            plugins: {
                legend: { 
                    position: 'bottom', 
                    labels: { color: '#e2e8f0', font: { size: 14 } } 
                }
            }
        }
    });
}

// Share function used in results_partial.html
window.shareResults = function () {
    const text = `My ${document.title} results`;
    if (navigator.share) {
        navigator.share({ title: document.title, text: text, url: window.location.href });
    } else {
        navigator.clipboard.writeText(window.location.href);
        alert("✅ Link copied to clipboard!");
    }
};