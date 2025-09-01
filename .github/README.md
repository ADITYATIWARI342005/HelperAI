# GitHub Activity Automation

This directory contains an automated GitHub activity system that generates realistic commit activity to maintain consistency in your GitHub contribution graph.

## How It Works

The system runs 12 times per day at random intervals and generates 4-26 commits daily with natural variance. It creates realistic-looking activity by:

1. **Daily Logs**: Updates activity logs with timestamps and random development activities
2. **Statistics**: Maintains repository statistics with realistic metrics
3. **Quotes**: Adds inspirational programming quotes to a daily collection

## Configuration

### `config/activity_config.json`

Controls the behavior of the automation:

```json
{
  "enabled": true,                    // Turn system on/off
  "update_types": ["log", "stats", "quote"],  // Types of updates to perform
  "max_changes_per_run": 3,          // Max changes per execution
  "schedule": {
    "commits_per_day_min": 4,        // Minimum commits per day
    "commits_per_day_max": 26        // Maximum commits per day
  },
  "maintenance": {
    "cleanup_old_logs": true,        // Auto-cleanup old files
    "max_log_entries": 365           // Keep logs for 1 year
  }
}
```

## Files Generated

### Activity Logs (`data/logs/`)
- Daily log files: `activity_YYYY-MM-DD.log`
- Contains timestamps and random development activities
- Examples: "Code review and optimization", "Bug fixes and improvements"

### Statistics (`data/stats/`)
- `repository_stats.json` - Tracks daily commit metrics
- Includes: commits count, lines added/removed, files changed
- Auto-cleanup after 30 days

### Quotes (`data/quotes/`)
- `daily_quotes.txt` - Collection of programming quotes
- Adds one quote per execution with timestamp
- 15 different inspirational programming quotes

## Schedule

The system runs at these times (UTC):
- 1:00 AM, 3:30 AM, 6:15 AM, 8:45 AM
- 10:30 AM, 12:15 PM, 2:45 PM, 4:30 PM  
- 6:15 PM, 8:45 PM, 10:30 PM, 12:15 AM

## Commit Messages

Generated commit messages include:
- "Update activity log - 2024-01-15"
- "Daily maintenance - Jan 15"
- "Routine update 2024/01/15"
- "Activity tracking update"
- And 10 more variations with different date formats

## Randomization

- **40% skip rate**: Randomly skips runs for natural variance
- **1-3 changes per run**: Randomly selects which updates to perform
- **Random timing**: Spreads activity throughout the day
- **Random content**: Different activities and quotes each time

## Manual Control

You can manually trigger the workflow:
1. Go to Actions tab in your repository
2. Select "Auto Commit Activity" workflow
3. Click "Run workflow" button

## Monitoring

Check the generated files to monitor activity:
- `data/logs/activity_YYYY-MM-DD.log` - Daily activity
- `data/stats/repository_stats.json` - Commit statistics
- `data/quotes/daily_quotes.txt` - Quote collection

## Customization

### Adding New Update Types

1. Add new function in `scripts/update_activity.py`
2. Add to `update_types` in config
3. Add case in main() function

### Changing Commit Range

Modify in `config/activity_config.json`:
- `commits_per_day_min` and `commits_per_day_max`
- Adjust `max_changes_per_run` and skip rate accordingly

### Custom Activities

Edit the `activities` list in `update_daily_log()` function to add your own development activities.

## Security

- Uses `GITHUB_TOKEN` for authentication
- Runs on GitHub's hosted runners
- No external dependencies or API calls
- All data is stored locally in the repository

## Troubleshooting

### No Commits Generated
1. Check if system is enabled in config
2. Verify workflow is running in Actions tab
3. Check for errors in workflow logs

### Too Many/Few Commits
1. Adjust `max_changes_per_run` in config
2. Modify skip rate in `update_activity.py`
3. Change number of scheduled runs in workflow

### Files Not Being Committed
1. Ensure `.gitignore` allows `data/` directory
2. Check workflow has proper permissions
3. Verify Git configuration in workflow
