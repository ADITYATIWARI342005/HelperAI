import random
import json
import os
from datetime import datetime, timedelta
import time

def ensure_directories():
    """Create necessary directories for storing activity data"""
    directories = ['data', 'data/logs', 'data/stats', 'data/quotes']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def load_config():
    """Load configuration from activity_config.json"""
    # Try multiple possible paths for the config file
    possible_paths = [
        '.github/config/activity_config.json',  # From scripts directory
        '../config/activity_config.json',       # From scripts directory
        'config/activity_config.json',          # From root directory
        '.github/config/activity_config.json'   # From root directory
    ]
    
    for config_path in possible_paths:
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            continue
        except json.JSONDecodeError:
            print(f"Invalid JSON in config file: {config_path}")
            continue
    
    print(f"Config file not found in any of these locations: {possible_paths}")
    return {}

def update_daily_log():
    """Update daily activity log with current timestamp and random activity"""
    log_dir = 'data/logs'
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(log_dir, f'activity_{today}.log')
    
    activities = [
        "Code review and optimization",
        "Bug fixes and improvements", 
        "Documentation updates",
        "Performance enhancements",
        "Feature implementation",
        "Testing and validation",
        "Code refactoring",
        "Security updates",
        "Dependency management",
        "Build system improvements"
    ]
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    activity = random.choice(activities)
    
    log_entry = f"[{timestamp}] {activity}\n"
    
    with open(log_file, 'a') as f:
        f.write(log_entry)
    
    print(f"Updated daily log: {activity}")

def update_stats():
    """Update statistics file with random metrics"""
    stats_dir = 'data/stats'
    stats_file = os.path.join(stats_dir, 'repository_stats.json')
    
    # Load existing stats or create new ones
    if os.path.exists(stats_file):
        try:
            with open(stats_file, 'r') as f:
                stats = json.load(f)
        except:
            stats = {}
    else:
        stats = {}
    
    # Update random metrics
    today = datetime.now().strftime('%Y-%m-%d')
    if today not in stats:
        stats[today] = {}
    
    stats[today].update({
        'commits': stats[today].get('commits', 0) + 1,
        'lines_added': random.randint(5, 50),
        'lines_removed': random.randint(1, 20),
        'files_changed': random.randint(1, 5),
        'last_updated': datetime.now().isoformat()
    })
    
    # Keep only last 30 days of stats
    cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    stats = {k: v for k, v in stats.items() if k >= cutoff_date}
    
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"Updated stats: {stats[today]['commits']} commits today")

def update_quote_file():
    """Update quote file with random inspirational quotes"""
    quotes_dir = 'data/quotes'
    quotes_file = os.path.join(quotes_dir, 'daily_quotes.txt')
    
    quotes = [
        "The best way to predict the future is to implement it. - Alan Kay",
        "Code is like humor. When you have to explain it, it's bad. - Cory House",
        "First, solve the problem. Then, write the code. - John Johnson",
        "Any fool can write code that a computer can understand. Good programmers write code that humans can understand. - Martin Fowler",
        "The only way to learn a new programming language is by writing programs in it. - Dennis Ritchie",
        "Sometimes it pays to stay in bed on Monday, rather than spending the rest of the week debugging Monday's code. - Dan Salomon",
        "It's not a bug – it's an undocumented feature. - Anonymous",
        "The most damaging phrase in the language is 'We've always done it this way!' - Grace Hopper",
        "Programming isn't about what you know; it's about what you can figure out. - Chris Pine",
        "The best error message is the one that never shows up. - Thomas Fuchs",
        "Good code is its own best documentation. - Steve McConnell",
        "Make it work, make it right, make it fast. - Kent Beck",
        "Code never lies, comments sometimes do. - Ron Jeffries",
        "Simplicity is the ultimate sophistication. - Leonardo da Vinci",
        "The only constant in the technology industry is change. - Marc Benioff"
    ]
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    quote = random.choice(quotes)
    
    quote_entry = f"[{timestamp}] {quote}\n"
    
    with open(quotes_file, 'a') as f:
        f.write(quote_entry)
    
    print(f"Updated quotes: {quote.split(' - ')[0]}")

def cleanup_old_logs(config):
    """Clean up old log entries based on configuration"""
    maintenance = config.get('maintenance', {})
    if not maintenance.get('cleanup_old_logs', True):
        return
    
    max_entries = maintenance.get('max_log_entries', 365)
    log_dir = 'data/logs'
    
    if not os.path.exists(log_dir):
        return
    
    # Get all log files and sort by date
    log_files = []
    for filename in os.listdir(log_dir):
        if filename.startswith('activity_') and filename.endswith('.log'):
            try:
                date_str = filename.replace('activity_', '').replace('.log', '')
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                log_files.append((date_obj, filename))
            except:
                continue
    
    log_files.sort(reverse=True)  # Newest first
    
    # Remove old files beyond max_entries
    if len(log_files) > max_entries:
        for _, filename in log_files[max_entries:]:
            filepath = os.path.join(log_dir, filename)
            try:
                os.remove(filepath)
                print(f"Cleaned up old log: {filename}")
            except:
                pass

def main():
    ensure_directories()
    config = load_config()
    
    if not config.get("enabled", True):
        print("Auto-commit activity is disabled in config.")
        return
    
    # Random chance to skip this run (to achieve 4-26 commits from 12 scheduled runs)
    # This gives us roughly 30-70% execution rate = 3.6-8.4 commits per day
    # With max_changes_per_run = 3, we can reach 26 commits on active days
    skip_chance = random.random()
    if skip_chance < 0.40:  # 40% chance to skip
        print("Randomly skipping this run to maintain natural variance.")
        return
    
    update_types = config.get("update_types", ["log", "stats", "quote"])
    max_changes = config.get("max_changes_per_run", 3)  # Reduced for more realistic commits
    
    # Randomly select which updates to perform (but at least one)
    selected_updates = random.sample(update_types, 
                                   min(random.randint(1, max_changes), len(update_types)))
    
    for update_type in selected_updates:
        if update_type == "log":
            update_daily_log()
        elif update_type == "stats":
            update_stats()
        elif update_type == "quote":
            update_quote_file()
    
    # Cleanup old logs
    cleanup_old_logs(config)
    
    print(f"Activity update completed. Performed: {', '.join(selected_updates)}")

if __name__ == "__main__":
    main()