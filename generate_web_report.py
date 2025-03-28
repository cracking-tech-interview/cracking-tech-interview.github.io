#!/usr/bin/env python3
import json
import os
import time
from leetcode_tracker import LeetCodeTracker

def generate_web_report():
    """Generate a JSON report for the web dashboard."""
    tracker = LeetCodeTracker()
    report_data = {
        "timestamp": int(time.time()),
        "submissions": []
    }
    
    # Get submissions report
    raw_report = tracker.generate_report()
    
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
            # Only include required data for the web report
            report_data["submissions"].append({
                "username": username,
                "title": submission.get("title", "Unknown Problem"),
                "titleSlug": submission.get("titleSlug", ""),
                "difficulty": submission.get("question", {}).get("difficulty", "Unknown"),
                "timestamp": submission.get("timestamp", 0),
                "domain": domain
            })
    
    # Save the report as JSON
    output_dir = "."
    with open(os.path.join(output_dir, "report_data.json"), "w") as f:
        json.dump(report_data, f, indent=2)
    
    print(f"Web report generated with {len(report_data['submissions'])} submissions.")

if __name__ == "__main__":
    generate_web_report() 