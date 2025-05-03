const form = document.getElementById('consultationForm');
const resultsDiv = document.getElementById('results');
const loading = document.querySelector('.loading');
const errorMsg = document.getElementById('errorMessage');

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const age = document.getElementById('age').value.trim();
    const gender = document.getElementById('gender').value.trim();
    const symptoms = document.getElementById('symptoms').value.trim();

    if (!age || !gender || !symptoms) {
        showError('Please fill all required fields');
        return;
    }

    try {
        showLoading();

        const response = await fetch('/api/consult', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ age, gender, symptoms })
        });

        const data = await response.json();

        if (!response.ok) throw new Error(data.error || 'Request failed');

        // Validate response structure (optional)
        if (!data.response.includes('## Repertorization Table') || !data.response.includes('## Remedy Selection')) {
            throw new Error('Please provide actual health symptoms for analysis.');
        }

        showResults(data.response);
    } catch (error) {
        showError(error.message);
    }
});

function showLoading() {
    loading.style.display = 'block';
    resultsDiv.style.display = 'none';
    errorMsg.textContent = '';
    errorMsg.style.display = 'none';
}

function showResults(content) {
    loading.style.display = 'none';
    resultsDiv.innerHTML = marked.parse(content);

    // Color 1/2/3 cells in all tables, but NOT in the Total row
    const tables = resultsDiv.querySelectorAll('table');
    tables.forEach(table => {
        Array.from(table.rows).forEach((row, idx) => {
            // Skip header row (idx === 0)
            // Skip "Total" row (last row)
            if (idx === 0 || row.cells[0].textContent.trim().toLowerCase() === 'total') return;
            Array.from(row.cells).forEach((cell, cidx) => {
                if (cidx === 0) return; // Don't color the first column (Symptom)
                const val = cell.textContent.trim();
                if (val === "1") cell.classList.add('col-green');
                else if (val === "2") cell.classList.add('col-blue');
                else if (val === "3") cell.classList.add('col-red');
            });
        });
    });

    // Highlight highest score in the table (last row)
    const table = resultsDiv.querySelector('table');
    if (table) {
        const totalRow = table.querySelector('tr:last-child');
        if (totalRow) {
            const cells = totalRow.querySelectorAll('td:not(:first-child)');
            let maxScore = 0;
            let maxIndex = -1;
            cells.forEach((cell, index) => {
                const score = parseInt(cell.textContent.replace(/\D/g, '')) || 0;
                if (score > maxScore) {
                    maxScore = score;
                    maxIndex = index;
                }
            });
            if (maxIndex >= 0) {
                cells[maxIndex].classList.add('highest-score');
            }
        }
    }

    // Highlight best remedy
    const remedyHeading = Array.from(resultsDiv.querySelectorAll('h2')).find(h2 => h2.textContent.includes('Remedy Selection'));
    if (remedyHeading) {
        const remedyStrong = remedyHeading.nextElementSibling?.querySelector('strong');
        if (remedyStrong) {
            remedyStrong.classList.add('best-remedy');
        }
    }

    resultsDiv.style.display = 'block';
}


function showError(message) {
    loading.style.display = 'none';
    resultsDiv.style.display = 'none';
    errorMsg.textContent = message;
    errorMsg.style.display = 'block';
}
