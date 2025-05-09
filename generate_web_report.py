#!/usr/bin/env python3
import json
import os
import time
from datetime import datetime, timedelta, timezone
from leetcode_tracker import LeetCodeTracker

def generate_web_report():
    """Generate a JSON report for the web dashboard."""
    tracker = LeetCodeTracker()
    report_data = {
        "timestamp": int(time.time()),
        "submissions": [],
        "all_users": []  # Add a new field to track all configured users
    }
    
    # Add all users to the report data
    for username in tracker.users:
        report_data["all_users"].append({
            "username": username,
            "domain": tracker.user_domains.get(username, "com"),
            "display_name": tracker.user_display_names.get(username, username)
        })
    
    # Get submissions report
    raw_report = tracker.generate_report()
    
    # Define UTC-7 timezone
    utc_minus_7 = timezone(timedelta(hours=-7))
    
    # Get today's date in UTC-7 for comparison
    today = datetime.now(utc_minus_7).date()
    
    # Process submissions
    for username in raw_report:
        user_data = raw_report[username]
        # Skip empty reports
        if not user_data or "submissions" not in user_data:
            continue
        
        # Get domain info for this user
        domain = tracker.user_domains.get(username, "com")
        
        # Add each submission
        for submission in user_data.get("submissions", []):
            # Convert timestamp to check if it's today in UTC-7
            submission_time = int(submission.get("timestamp", 0))
            submission_date = datetime.fromtimestamp(submission_time, utc_minus_7).date()
            is_today = (submission_date == today)
            
            # Only include required data for the web report
            report_data["submissions"].append({
                "username": username,
                "title": submission.get("title", "Unknown Problem"),
                "titleSlug": submission.get("titleSlug", ""),
                "difficulty": submission.get("question", {}).get("difficulty", "Unknown"),
                "timestamp": submission.get("timestamp", 0),
                "domain": domain,
                "isToday": is_today
            })
    
    # Save the report as JSON
    output_dir = "."
    with open(os.path.join(output_dir, "report_data.json"), "w") as f:
        json.dump(report_data, f, indent=2)
    
    print(f"Web report generated with {len(report_data['submissions'])} submissions.")

if __name__ == "__main__":
    generate_web_report() 