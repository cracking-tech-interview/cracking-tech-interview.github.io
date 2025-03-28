document.addEventListener('DOMContentLoaded', function() {
    // Fetch the data from the JSON file
    fetch('report_data.json')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            updateLastUpdatedTime(data.timestamp);
            renderTodaySummary(data);
            renderSubmissionsTable(data.submissions);
            renderDifficultyChart(data);
            renderActivityChart(data);
        })
        .catch(error => {
            console.error('Error fetching data:', error);
            document.getElementById('today-summary').innerHTML = `
                <div class="col-12 text-center py-5">
                    <div class="alert alert-danger">
                        Error loading data. Please try again later.
                    </div>
                </div>
            `;
        });
});

function updateLastUpdatedTime(timestamp) {
    const date = new Date(timestamp * 1000);
    document.querySelector('#last-updated span').textContent = date.toLocaleString();
}

function renderTodaySummary(data) {
    const users = [...new Set(data.submissions.map(s => s.username))];
    const easyCount = data.submissions.filter(s => s.difficulty === 'Easy').length;
    const mediumCount = data.submissions.filter(s => s.difficulty === 'Medium').length;
    const hardCount = data.submissions.filter(s => s.difficulty === 'Hard').length;
    const totalProblems = data.submissions.length;

    let summaryHTML = '';
    
    // Add user stats
    summaryHTML += `
        <div class="col-md-3 col-sm-6 mb-3">
            <div class="stat-card">
                <div class="stat-number">${users.length}</div>
                <div class="stat-label">Active Users</div>
            </div>
        </div>
        <div class="col-md-3 col-sm-6 mb-3">
            <div class="stat-card">
                <div class="stat-number">${totalProblems}</div>
                <div class="stat-label">Solved Today</div>
            </div>
        </div>
    `;

    // Add difficulty distribution
    summaryHTML += `
        <div class="col-md-6 mb-3">
            <div class="stat-card">
                <div class="d-flex justify-content-around">
                    <div>
                        <div class="stat-number text-success">${easyCount}</div>
                        <div class="stat-label">Easy</div>
                    </div>
                    <div>
                        <div class="stat-number text-warning">${mediumCount}</div>
                        <div class="stat-label">Medium</div>
                    </div>
                    <div>
                        <div class="stat-number text-danger">${hardCount}</div>
                        <div class="stat-label">Hard</div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Per-user breakdown
    summaryHTML += `
        <div class="col-12 mt-3">
            <h5>User Activity</h5>
            <div class="row">
    `;

    users.forEach(user => {
        const userSubmissions = data.submissions.filter(s => s.username === user);
        const userEasy = userSubmissions.filter(s => s.difficulty === 'Easy').length;
        const userMedium = userSubmissions.filter(s => s.difficulty === 'Medium').length;
        const userHard = userSubmissions.filter(s => s.difficulty === 'Hard').length;
        
        summaryHTML += `
            <div class="col-md-4 col-sm-6 mb-3">
                <div class="card h-100">
                    <div class="card-body">
                        <h6 class="card-title">${user}</h6>
                        <div class="d-flex justify-content-between">
                            <span class="difficulty-badge difficulty-easy">${userEasy} Easy</span>
                            <span class="difficulty-badge difficulty-medium">${userMedium} Medium</span>
                            <span class="difficulty-badge difficulty-hard">${userHard} Hard</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    summaryHTML += `
            </div>
        </div>
    `;

    document.getElementById('today-summary').innerHTML = summaryHTML;
}

function renderSubmissionsTable(submissions) {
    const tableBody = document.querySelector('#submissions-table tbody');
    let tableHTML = '';

    // Sort submissions by timestamp (newest first)
    const sortedSubmissions = [...submissions].sort((a, b) => b.timestamp - a.timestamp);

    sortedSubmissions.forEach(submission => {
        const date = new Date(submission.timestamp * 1000);
        const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        const difficultyClass = submission.difficulty.toLowerCase();

        let problemLink;
        if (submission.domain === 'cn') {
            problemLink = `https://leetcode.cn/problems/${submission.titleSlug}/`;
        } else {
            problemLink = `https://leetcode.com/problems/${submission.titleSlug}/`;
        }

        tableHTML += `
            <tr>
                <td>${submission.username}</td>
                <td>
                    <a href="${problemLink}" target="_blank" class="problem-link">
                        ${submission.title}
                    </a>
                </td>
                <td><span class="difficulty-badge difficulty-${difficultyClass}">${submission.difficulty}</span></td>
                <td>${timeStr}</td>
            </tr>
        `;
    });

    tableBody.innerHTML = tableHTML;
}

function renderDifficultyChart(data) {
    const ctx = document.getElementById('difficulty-chart').getContext('2d');
    
    const easyCount = data.submissions.filter(s => s.difficulty === 'Easy').length;
    const mediumCount = data.submissions.filter(s => s.difficulty === 'Medium').length;
    const hardCount = data.submissions.filter(s => s.difficulty === 'Hard').length;
    const unknownCount = data.submissions.filter(s => s.difficulty === 'Unknown').length;

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Easy', 'Medium', 'Hard', 'Unknown'],
            datasets: [{
                data: [easyCount, mediumCount, hardCount, unknownCount],
                backgroundColor: [
                    getComputedStyle(document.documentElement).getPropertyValue('--easy-color'),
                    getComputedStyle(document.documentElement).getPropertyValue('--medium-color'),
                    getComputedStyle(document.documentElement).getPropertyValue('--hard-color'),
                    '#6c757d'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function renderActivityChart(data) {
    const ctx = document.getElementById('activity-chart').getContext('2d');
    
    // Group submissions by hour
    const submissionsByHour = {};
    
    // Initialize all hours to 0
    for (let i = 0; i < 24; i++) {
        submissionsByHour[i] = 0;
    }
    
    // Count submissions per hour
    data.submissions.forEach(submission => {
        const date = new Date(submission.timestamp * 1000);
        const hour = date.getHours();
        submissionsByHour[hour]++;
    });
    
    // Convert to arrays for Chart.js
    const hours = [];
    const counts = [];
    
    for (let i = 0; i < 24; i++) {
        const hourLabel = i.toString().padStart(2, '0') + ':00';
        hours.push(hourLabel);
        counts.push(submissionsByHour[i]);
    }
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hours,
            datasets: [{
                label: 'Submissions',
                data: counts,
                backgroundColor: 'rgba(54, 162, 235, 0.5)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
} 