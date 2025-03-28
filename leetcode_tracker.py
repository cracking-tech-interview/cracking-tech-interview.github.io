#!/usr/bin/env python3
import json
import requests
from datetime import datetime, timedelta
import time
from collections import defaultdict
import sys
from tabulate import tabulate
import re

class LeetCodeTracker:
    def __init__(self, config_file="config.json"):
        """Initialize the tracker with configuration."""
        try:
            with open(config_file, 'r') as f:
                self.config = json.load(f)
            
            # Support both simple username list and detailed user config
            users_config = self.config.get("users", [])
            self.users = []
            self.user_domains = {}
            
            # Parse users configuration
            for user in users_config:
                if isinstance(user, str):
                    # Simple username format - default to leetcode.com
                    self.users.append(user)
                    self.user_domains[user] = "com"
                elif isinstance(user, dict):
                    # Detailed user config with domain specification
                    username = user.get("username")
                    domain = user.get("domain", "com")
                    if username:
                        self.users.append(username)
                        self.user_domains[username] = domain
            
            self.days_to_track = self.config.get("days_to_track", 1)
            
            # New option to enable/disable fetching total stats
            self.fetch_total_stats = self.config.get("fetch_total_stats", True)
            
            # New option for minimum submissions threshold
            self.min_submissions = self.config.get("min_submissions", 0)
            
            if not self.users:
                print("Error: No users specified in config file.")
                sys.exit(1)
                
        except FileNotFoundError:
            print(f"Error: Config file '{config_file}' not found.")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Config file '{config_file}' is not valid JSON.")
            sys.exit(1)
            
        # Base headers for API requests
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
    def get_api_url(self, username):
        """Get the appropriate API URL based on user domain."""
        # Only used for non-CN sites now
        return "https://leetcode.com/graphql"

    def get_user_activity(self, username):
        """Fetch a user's recent submissions from LeetCode."""
        domain = self.user_domains.get(username, "com")
        is_cn = domain.lower() == "cn"
        
        if is_cn:
            # Use regular REST API for LeetCode China
            return self.get_cn_user_activity(username)
        else:
            # Continue using GraphQL for international site
            return self.get_intl_user_activity(username)

    def get_cn_user_activity(self, username):
        """Fetch a user's recent submissions from LeetCode.cn using the correct API endpoint."""
        # Create a session with cookies
        session = requests.Session()
        profile_url = f"https://leetcode.cn/u/{username}/"
        
        # Set up headers for browser simulation
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        try:
            # Visit the profile page to get cookies
            profile_response = session.get(profile_url, headers=headers)
            if profile_response.status_code != 200:
                print(f"Failed to access profile page for {username}: HTTP {profile_response.status_code}")
                return []
            
            # Check if we can extract CSRF token from the page
            csrf_token = None
            if 'csrftoken' in session.cookies:
                csrf_token = session.cookies['csrftoken']
            
            # Use the correct API endpoint for LeetCode.cn
            api_url = "https://leetcode.cn/graphql/noj-go/"
            
            # Remove the difficulty field which is causing the error
            query = """
            query recentAcSubmissions($userSlug: String!) {
              recentACSubmissions(userSlug: $userSlug) {
                submissionId
                submitTime
                question {
                  title
                  translatedTitle
                  titleSlug
                  questionFrontendId
                }
              }
            }
            """
            
            variables = {
                "userSlug": username
            }
            
            # Prepare headers for the API request
            api_headers = headers.copy()
            api_headers["Content-Type"] = "application/json"
            api_headers["Referer"] = profile_url
            api_headers["Origin"] = "https://leetcode.cn"
            if csrf_token:
                api_headers["X-CSRFToken"] = csrf_token
            
            # Make the API request with the correct operation name
            payload = {
                "operationName": "recentAcSubmissions",
                "query": query,
                "variables": variables
            }
            
            graphql_response = session.post(api_url, json=payload, headers=api_headers)
            
            if graphql_response.status_code == 200:
                data = graphql_response.json()
                submissions = data.get("data", {}).get("recentACSubmissions", [])
                
                # Convert to our standard format
                ac_submissions = []
                for s in submissions:
                    question = s.get("question", {})
                    
                    # Check if this submission is within our date range
                    timestamp = s.get("submitTime")
                    if timestamp:
                        timestamp = int(timestamp)
                        submission_date = datetime.fromtimestamp(timestamp).date()
                        
                        # If the submission date is too old, skip it
                        today = datetime.now().date()
                        if (today - submission_date).days > self.days_to_track:
                            continue
                    
                    # Get problem difficulty separately
                    title_slug = question.get("titleSlug")
                    problem_data = {"difficulty": "Unknown"}
                    if title_slug:
                        problem_data = self.get_cn_problem_data(title_slug, session)
                        time.sleep(0.3)  # Short delay to avoid rate limiting
                    
                    ac_submissions.append({
                        "id": s.get("submissionId"),
                        "title": question.get("title") or question.get("translatedTitle"),
                        "titleSlug": title_slug,
                        "timestamp": timestamp,
                        "question": {
                            "questionFrontendId": question.get("questionFrontendId"),
                            "difficulty": problem_data.get("difficulty", "Unknown")
                        }
                    })
                
                return ac_submissions
                
            else:
                print(f"GraphQL request failed for {username}: HTTP {graphql_response.status_code}")
                print(f"Response: {graphql_response.text[:500]}...")
                return []
                
        except Exception as e:
            print(f"Error fetching data for {username}: {str(e)}")
            return []

    def get_cn_problem_data(self, title_slug, session):
        """Fetch problem difficulty and ID for a given problem from LeetCode.cn."""
        if not title_slug:
            return {"questionFrontendId": "", "difficulty": "Unknown"}
        
        problem_url = f"https://leetcode.cn/problems/{title_slug}/"
        
        try:
            # First try to get the data from the problem page directly
            response = session.get(problem_url)
            
            if response.status_code == 200:
                # Try to extract question ID and difficulty from the HTML
                html_content = response.text
                
                # Simple pattern matching to extract data from the page
                question_id = ""
                difficulty = "Unknown"
                
                # Look for question ID pattern
                id_match = re.search(r'"questionId":\s*"(\d+)"', html_content)
                if id_match:
                    question_id = id_match.group(1)
                
                # Look for difficulty level
                if "difficulty: 'Easy'" in html_content or '"difficulty":"Easy"' in html_content:
                    difficulty = "Easy"
                elif "difficulty: 'Medium'" in html_content or '"difficulty":"Medium"' in html_content:
                    difficulty = "Medium"
                elif "difficulty: 'Hard'" in html_content or '"difficulty":"Hard"' in html_content:
                    difficulty = "Hard"
                
                return {
                    "questionFrontendId": question_id,
                    "difficulty": difficulty
                }
        except Exception as e:
            print(f"Error fetching problem data for {title_slug}: {str(e)}")
        
        # Return default values if we couldn't extract the data
        return {"questionFrontendId": "", "difficulty": "Unknown"}

    def get_intl_user_activity(self, username):
        """Fetch a user's recent submissions from LeetCode.com using GraphQL."""
        query = """
        query recentAcSubmissions($username: String!, $limit: Int!) {
          recentAcSubmissionList(username: $username, limit: $limit) {
            id
            title
            titleSlug
            timestamp
          }
        }
        """
        
        limit = self.days_to_track * 10
        variables = {
            "username": username,
            "limit": limit
        }
        
        try:
            api_url = self.get_api_url(username)
            response = requests.post(
                api_url,
                json={"query": query, "variables": variables},
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                submissions = data.get("data", {}).get("recentAcSubmissionList", [])
                
                # Enhance submissions with difficulty data
                for submission in submissions:
                    title_slug = submission.get("titleSlug")
                    if title_slug:
                        problem_data = self.get_problem_data(title_slug, username)
                        submission["question"] = problem_data
                        time.sleep(0.5)
                
                return submissions
            else:
                print(f"Error fetching data for {username}: HTTP {response.status_code}")
                print(f"Response: {response.text[:500]}...")
                return []
                
        except Exception as e:
            print(f"Error fetching data for {username}: {str(e)}")
            return []

    def get_problem_data(self, title_slug, username):
        """Fetch problem difficulty and ID for a given problem."""
        domain = self.user_domains.get(username, "com")
        is_cn = domain.lower() == "cn"
        
        # Different field names for CN site
        if is_cn:
            query = """
            query questionData($titleSlug: String!) {
              question(titleSlug: $titleSlug) {
                questionId
                difficulty
              }
            }
            """
        else:
            query = """
            query questionData($titleSlug: String!) {
              question(titleSlug: $titleSlug) {
                questionFrontendId
                difficulty
              }
            }
            """
        
        variables = {
            "titleSlug": title_slug
        }
        
        try:
            api_url = self.get_api_url(username)
            headers = self.headers.copy()
            
            if is_cn:
                headers["Referer"] = f"https://leetcode.cn/problems/{title_slug}/"
                headers["Origin"] = "https://leetcode.cn"
                headers["Accept-Language"] = "zh-CN,zh;q=0.9,en;q=0.8"
            
            response = requests.post(
                api_url,
                json={"query": query, "variables": variables},
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                question_data = data.get("data", {}).get("question", {})
                
                # Normalize field names between sites
                if is_cn and "questionId" in question_data:
                    question_data["questionFrontendId"] = question_data["questionId"]
                
                return question_data
            else:
                print(f"Problem data fetch error for {title_slug}: HTTP {response.status_code}")
                return {}
            
        except Exception as e:
            print(f"Problem data fetch error: {str(e)}")
            return {}
    
    def generate_report(self):
        """Generate a report of daily submission counts for all users."""
        # Get current date and calculate date range
        today = datetime.now().date()
        date_range = [today - timedelta(days=i) for i in range(self.days_to_track)]
        date_range.reverse()  # Oldest to newest
        
        # Dictionary to store submission counts by user, date and difficulty
        submission_counts = defaultdict(lambda: defaultdict(int))
        difficulty_counts = defaultdict(lambda: {"Easy": 0, "Medium": 0, "Hard": 0})
        question_numbers = defaultdict(set)
        total_stats = {}
        
        # Fetch and process data for each user
        for username in self.users:
            print(f"Fetching data for {username}...")
            
            # Get total stats first (if enabled)
            if self.fetch_total_stats:
                user_stats = self.get_user_stats(username)
                total_stats[username] = user_stats
            
            # Then get recent submissions
            submissions = self.get_user_activity(username)
            
            for submission in submissions:
                # Convert timestamp to date
                timestamp = submission.get("timestamp")
                if timestamp:
                    # Convert the timestamp string to an integer
                    timestamp = int(timestamp)
                    submission_date = datetime.fromtimestamp(timestamp).date()
                    
                    # Only count submissions within our date range
                    if submission_date >= date_range[0] and submission_date <= date_range[-1]:
                        submission_counts[username][submission_date] += 1
                        
                        # Track difficulty
                        difficulty = submission.get("question", {}).get("difficulty", "Unknown")
                        if difficulty in ["Easy", "Medium", "Hard"]:
                            difficulty_counts[username][difficulty] += 1
                        
                        # Track question numbers
                        question_id = submission.get("question", {}).get("questionFrontendId")
                        if question_id:
                            question_numbers[username].add(question_id)
            
            # Avoid hitting rate limits
            time.sleep(1)
        
        # Handle the case when no submissions are found
        if not any(submission_counts.values()):
            print("\nLeetCode Submission Report\n")
            print(f"Report Date: {today.strftime('%Y-%m-%d')}")
            print("No submissions found in the specified date range.")
            print(f"\nReport generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            return
        
        # Define headers based on whether total stats are included
        if self.fetch_total_stats:
            headers = ["User", "Recent", "Easy", "Medium", "Hard", "Unique", "Total Solved", "E", "M", "H"]
        else:
            headers = ["User", "Recent", "Easy", "Medium", "Hard", "Unique"]
        
        main_rows = []
        below_threshold_rows = []
        
        for username in self.users:
            user_total = sum(submission_counts[username].values())
            easy_count = difficulty_counts[username]["Easy"]
            medium_count = difficulty_counts[username]["Medium"]
            hard_count = difficulty_counts[username]["Hard"]
            unique_problems = len(question_numbers[username])
            
            # Create row with or without total stats
            if self.fetch_total_stats:
                # Add total stats
                user_stats = total_stats.get(username, {"Total": 0, "Easy": 0, "Medium": 0, "Hard": 0})
                
                row = [
                    username, 
                    user_total, 
                    easy_count, 
                    medium_count, 
                    hard_count, 
                    unique_problems,
                    user_stats["Total"],
                    user_stats["Easy"],
                    user_stats["Medium"],
                    user_stats["Hard"]
                ]
            else:
                row = [
                    username, 
                    user_total, 
                    easy_count, 
                    medium_count, 
                    hard_count, 
                    unique_problems
                ]
            
            # Separate users who meet the threshold from those who don't
            if user_total >= self.min_submissions:
                main_rows.append(row)
            else:
                below_threshold_rows.append(row)
        
        # Print the main report
        print("\nLeetCode Submission Report\n")
        print(f"Report Date: {today.strftime('%Y-%m-%d')}")
        
        # Add info about the minimum submissions threshold if set
        if self.min_submissions > 0:
            print(f"Users with {self.min_submissions}+ submissions:")
        
        if main_rows:
            print(tabulate(main_rows, headers=headers, tablefmt="grid"))
        else:
            print("No users met the minimum submission threshold.")
        
        # Print the below threshold table if needed and if any exist
        if below_threshold_rows and self.min_submissions > 0:
            print(f"\nUsers with fewer than {self.min_submissions} submissions:")
            print(tabulate(below_threshold_rows, headers=headers, tablefmt="grid"))
        
        if self.fetch_total_stats:
            print("\nRecent = Submissions in tracked period | E/M/H = Total problems by difficulty")
        else:
            print("\nOnly showing recent submissions in the tracked period")
        
        print(f"\nReport generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def get_user_stats(self, username):
        """Fetch a user's total statistics (accepted problems by difficulty)."""
        domain = self.user_domains.get(username, "com")
        is_cn = domain.lower() == "cn"
        
        if is_cn:
            return self.get_cn_user_stats(username)
        else:
            return self.get_intl_user_stats(username)

    def get_intl_user_stats(self, username):
        """Fetch total statistics for LeetCode.com users."""
        query = """
        query userProblemsSolved($username: String!) {
          matchedUser(username: $username) {
            submitStats: submitStatsGlobal {
              acSubmissionNum {
                difficulty
                count
                submissions
              }
            }
          }
        }
        """
        
        variables = {
            "username": username
        }
        
        try:
            api_url = self.get_api_url(username)
            response = requests.post(
                api_url,
                json={"query": query, "variables": variables},
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                stats = data.get("data", {}).get("matchedUser", {}).get("submitStats", {}).get("acSubmissionNum", [])
                
                # Convert to our standard format
                result = {
                    "Easy": 0,
                    "Medium": 0,
                    "Hard": 0,
                    "Total": 0
                }
                
                for item in stats:
                    difficulty = item.get("difficulty")
                    count = item.get("count", 0)
                    
                    if difficulty == "Easy":
                        result["Easy"] = count
                    elif difficulty == "Medium":
                        result["Medium"] = count
                    elif difficulty == "Hard":
                        result["Hard"] = count
                    elif difficulty == "All":
                        result["Total"] = count
                
                # Calculate total if not provided
                if result["Total"] == 0:
                    result["Total"] = result["Easy"] + result["Medium"] + result["Hard"]
                    
                return result
            else:
                print(f"Error fetching stats for {username}: HTTP {response.status_code}")
                return {"Easy": 0, "Medium": 0, "Hard": 0, "Total": 0}
        except Exception as e:
            print(f"Error fetching stats for {username}: {str(e)}")
            return {"Easy": 0, "Medium": 0, "Hard": 0, "Total": 0}

    def get_cn_user_stats(self, username):
        """Fetch total statistics for LeetCode.cn users."""
        # Create a session with cookies
        session = requests.Session()
        profile_url = f"https://leetcode.cn/u/{username}/"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        }
        
        try:
            # First visit the profile page to get cookies
            session.get(profile_url, headers=headers)
            
            # Now query the user stats using the correct endpoint
            api_url = "https://leetcode.cn/graphql/noj-go/"
            
            # Use the userProfile query which is more stable
            query = """
            query userProfile($userSlug: String!) {
              userProfile(userSlug: $userSlug) {
                submitStats {
                  acSubmissionNum {
                    difficulty
                    count
                  }
                }
              }
            }
            """
            
            variables = {
                "userSlug": username
            }
            
            api_headers = headers.copy()
            api_headers["Content-Type"] = "application/json"
            api_headers["Referer"] = profile_url
            api_headers["Origin"] = "https://leetcode.cn"
            
            if 'csrftoken' in session.cookies:
                api_headers["X-CSRFToken"] = session.cookies['csrftoken']
            
            payload = {
                "operationName": "userProfile",
                "query": query,
                "variables": variables
            }
            
            response = session.post(api_url, json=payload, headers=api_headers)
            
            if response.status_code == 200:
                data = response.json()
                stats = data.get("data", {}).get("userProfile", {}).get("submitStats", {}).get("acSubmissionNum", [])
                
                # Convert to our standard format
                result = {
                    "Easy": 0,
                    "Medium": 0,
                    "Hard": 0,
                    "Total": 0
                }
                
                for item in stats:
                    difficulty = item.get("difficulty")
                    count = item.get("count", 0)
                    
                    if difficulty == "EASY" or difficulty == "Easy":
                        result["Easy"] = count
                    elif difficulty == "MEDIUM" or difficulty == "Medium":
                        result["Medium"] = count
                    elif difficulty == "HARD" or difficulty == "Hard":
                        result["Hard"] = count
                    elif difficulty == "ALL" or difficulty == "All":
                        result["Total"] = count
                
                # Calculate total if not provided
                if result["Total"] == 0:
                    result["Total"] = result["Easy"] + result["Medium"] + result["Hard"]
                    
                return result
                
            else:
                print(f"Error fetching stats for {username}: HTTP {response.status_code}")
                print(f"Response: {response.text[:500]}...")
                
                # Try to get stats by scraping the profile page as fallback
                try:
                    html_content = session.get(profile_url).text
                    if html_content:
                        # Extract total solved problems using regex
                        solved_match = re.search(r'\"totalSolved\":(\d+)', html_content)
                        easy_match = re.search(r'\"easySolved\":(\d+)', html_content)
                        medium_match = re.search(r'\"mediumSolved\":(\d+)', html_content)
                        hard_match = re.search(r'\"hardSolved\":(\d+)', html_content)
                        
                        result = {
                            "Easy": int(easy_match.group(1)) if easy_match else 0,
                            "Medium": int(medium_match.group(1)) if medium_match else 0,
                            "Hard": int(hard_match.group(1)) if hard_match else 0,
                            "Total": int(solved_match.group(1)) if solved_match else 0
                        }
                        
                        # Calculate total if needed
                        if result["Total"] == 0:
                            result["Total"] = result["Easy"] + result["Medium"] + result["Hard"]
                        
                        return result
                except Exception as e:
                    print(f"Fallback extraction failed: {e}")
                    
                return {"Easy": 0, "Medium": 0, "Hard": 0, "Total": 0}
                
        except Exception as e:
            print(f"Error fetching stats for {username}: {str(e)}")
            return {"Easy": 0, "Medium": 0, "Hard": 0, "Total": 0}

if __name__ == "__main__":
    tracker = LeetCodeTracker()
    tracker.generate_report() 