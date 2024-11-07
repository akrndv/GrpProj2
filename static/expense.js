const expenseForm = document.getElementById('expenseForm');
const expenseChart = document.getElementById('expenseChart');
let categories = [];
let amounts = [];

const chart = new Chart(expenseChart, {
    type: 'bar',
    data: {
        labels: categories,
        datasets: [{
            label: 'Daily Expenses',
            data: amounts,
            backgroundColor: 'rgba(75, 192, 192, 0.6)',
            borderColor: 'rgba(75, 192, 192, 1)',
            borderWidth: 1
        }]
    },
    options: {
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});

expenseForm.addEventListener('submit', (e) => {
    e.preventDefault();

    const category = document.getElementById('category').value;
    const amount = parseFloat(document.getElementById('amount').value);

    // Check if category already exists
    const existingIndex = categories.indexOf(category);
    if (existingIndex !== -1) {
        amounts[existingIndex] += amount; // Update existing category
    } else {
        categories.push(category);
        amounts.push(amount); // Add new category
    }

    // Update chart data
    chart.data.labels = categories;
    chart.data.datasets[0].data = amounts;
    chart.update();

    // Reset form fields
    expenseForm.reset();
});