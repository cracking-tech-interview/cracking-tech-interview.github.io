document.addEventListener('DOMContentLoaded', function() {
    // Fetch the data from the JSON file with cache-busting
    const timestamp = new Date().getTime(); // Current timestamp for cache busting
    const url = `report_data.json?t=${timestamp}`;
    
    fetch(url, {
        method: 'GET',
        headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        },
        cache: 'no-store' // Force fresh fetch
    })
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
    let summaryHTML = '';
    
    // Use all_users if available, otherwise fall back to extracting users from submissions
    const allUsers = data.all_users ? 
        data.all_users.map(u => u.username) : 
        [...new Set(data.submissions.map(s => s.username))];
    
    // Count problems by difficulty (only from today)
    const todaySubmissions = data.submissions.filter(s => s.isToday);
    const easyCount = todaySubmissions.filter(s => s.difficulty === 'Easy').length;
    const mediumCount = todaySubmissions.filter(s => s.difficulty === 'Medium').length;
    const hardCount = todaySubmissions.filter(s => s.difficulty === 'Hard').length;
    const totalProblems = todaySubmissions.length;
    
    // Group users by their completion status
    const usersWithSubmissionsToday = [];
    const usersWithoutSubmissionsToday = [];
    
    allUsers.forEach(user => {
        // Check if user has any submissions today
        const userSubmissionsToday = data.submissions.filter(s => 
            s.username === user && s.isToday
        );
        
        if (userSubmissionsToday.length > 0) {
            usersWithSubmissionsToday.push(user);
        } else {
            usersWithoutSubmissionsToday.push(user);
        }
    });

    // CHANGED ORDER: First display users without submissions today (incomplete check-ins)
    if (usersWithoutSubmissionsToday.length > 0) {
        summaryHTML += `
            <div class="col-12">
                <div class="alert alert-warning">
                    <h5>⚠️ Users Missing Today's Check-in</h5>
                </div>
                <div class="row">
        `;

        usersWithoutSubmissionsToday.forEach(user => {
            summaryHTML += `
                <div class="col-md-4 col-sm-6 mb-3">
                    <div class="card h-100 border-warning">
                        <div class="card-body">
                            <h6 class="card-title">${user}</h6>
                            <p class="text-danger">No submissions today</p>
                        </div>
                    </div>
                </div>
            `;
        });

        summaryHTML += `
                </div>
            </div>
        `;
    }

    // Next display users with submissions today (completed check-ins)
    if (usersWithSubmissionsToday.length > 0) {
        summaryHTML += `
            <div class="col-12 mt-3">
                <div class="alert alert-success">
                    <h5>✅ Users Who Completed Today's Check-in</h5>
                </div>
                <div class="row">
        `;

        usersWithSubmissionsToday.forEach(user => {
            // Only count today's submissions for this user
            const userTodaySubmissions = data.submissions.filter(s => s.username === user && s.isToday);
            const userEasy = userTodaySubmissions.filter(s => s.difficulty === 'Easy').length;
            const userMedium = userTodaySubmissions.filter(s => s.difficulty === 'Medium').length;
            const userHard = userTodaySubmissions.filter(s => s.difficulty === 'Hard').length;
            
            summaryHTML += `
                <div class="col-md-4 col-sm-6 mb-3">
                    <div class="card h-100 border-success">
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
    }
    
    // Finally add the main statistics at the bottom
    summaryHTML += `
        <div class="col-12 mt-3">
            <div class="alert alert-primary">
                <h5>📊 Overall Statistics</h5>
            </div>
            <div class="row">
                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="stat-card">
                        <div class="stat-number">${allUsers.length}</div>
                        <div class="stat-label">Active Users</div>
                    </div>
                </div>
                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="stat-card">
                        <div class="stat-number">${totalProblems}</div>
                        <div class="stat-label">Solved Today</div>
                    </div>
                </div>
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
        const dateStr = date.toLocaleDateString();
        
        const difficultyClass = submission.difficulty.toLowerCase();
        const rowClass = submission.isToday ? 'table-success' : '';

        let problemLink;
        if (submission.domain === 'cn') {
            problemLink = `https://leetcode.cn/problems/${submission.titleSlug}/`;
        } else {
            problemLink = `https://leetcode.com/problems/${submission.titleSlug}/`;
        }

        tableHTML += `
            <tr class="${rowClass}">
                <td>${submission.username}</td>
                <td>
                    <a href="${problemLink}" target="_blank" class="problem-link">
                        ${submission.title}
                    </a>
                </td>
                <td><span class="difficulty-badge difficulty-${difficultyClass}">${submission.difficulty}</span></td>
                <td>${submission.isToday ? timeStr : dateStr + ' ' + timeStr}</td>
            </tr>
        `;
    });

    tableBody.innerHTML = tableHTML;
}

function renderDifficultyChart(data) {
    const ctx = document.getElementById('difficulty-chart').getContext('2d');
    
    // Separate today's submissions
    const todaySubmissions = data.submissions.filter(s => s.isToday);
    
    // Count by difficulty for today
    const easyCount = todaySubmissions.filter(s => s.difficulty === 'Easy').length;
    const mediumCount = todaySubmissions.filter(s => s.difficulty === 'Medium').length;
    const hardCount = todaySubmissions.filter(s => s.difficulty === 'Hard').length;
    const unknownCount = todaySubmissions.filter(s => s.difficulty === 'Unknown').length;

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Easy', 'Medium', 'Hard', 'Unknown'],
            datasets: [{
                label: 'Today\'s Submissions',
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
                },
                title: {
                    display: true,
                    text: 'Today\'s Submissions by Difficulty'
                }
            }
        }
    });
}

function renderActivityChart(data) {
    const ctx = document.getElementById('activity-chart').getContext('2d');
    
    // Separate today's submissions
    const todaySubmissions = data.submissions.filter(s => s.isToday);
    const previousSubmissions = data.submissions.filter(s => !s.isToday);
    
    // Group submissions by hour
    const todayByHour = {};
    const previousByHour = {};
    
    // Initialize all hours to 0
    for (let i = 0; i < 24; i++) {
        todayByHour[i] = 0;
        previousByHour[i] = 0;
    }
    
    // Count today's submissions per hour
    todaySubmissions.forEach(submission => {
        const date = new Date(submission.timestamp * 1000);
        const hour = date.getHours();
        todayByHour[hour]++;
    });
    
    // Count previous submissions per hour (average per day)
    previousSubmissions.forEach(submission => {
        const date = new Date(submission.timestamp * 1000);
        const hour = date.getHours();
        previousByHour[hour]++;
    });
    
    // Convert to arrays for Chart.js
    const hours = [];
    const todayCounts = [];
    const previousCounts = [];
    
    for (let i = 0; i < 24; i++) {
        const hourLabel = i.toString().padStart(2, '0') + ':00';
        hours.push(hourLabel);
        todayCounts.push(todayByHour[i]);
        
        // Calculate average for previous days if we have multiple days of data
        // For simplicity, we'll just show the raw counts
        previousCounts.push(previousByHour[i]);
    }
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hours,
            datasets: [
                {
                    label: 'Today',
                    data: todayCounts,
                    backgroundColor: 'rgba(40, 167, 69, 0.7)',
                    borderColor: 'rgba(40, 167, 69, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Previous Days',
                    data: previousCounts,
                    backgroundColor: 'rgba(108, 117, 125, 0.3)',
                    borderColor: 'rgba(108, 117, 125, 0.7)',
                    borderWidth: 1
                }
            ]
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