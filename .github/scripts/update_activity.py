def main():
    ensure_directories()
    config = load_config()
    
    if not config.get("enabled", True):
        print("Auto-commit activity is disabled in config.")
        return
    
    # Random chance to skip this run (to achieve 8-18 commits from 12 scheduled runs)
    # This gives us roughly 60-80% execution rate = 7.2-9.6 commits per day
    # With max_changes_per_run = 5, we can reach 18 commits on active days
    skip_chance = random.random()
    if skip_chance < 0.25:  # 25% chance to skip (reduced from 30%)
        print("Randomly skipping this run to maintain natural variance.")
        return
    
    update_types = config.get("update_types", ["log", "stats"])
    max_changes = config.get("max_changes_per_run", 5)  # Increased from 2
    
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
    
    print(f"Activity update completed. Performed: {', '.join(selected_updates)}")