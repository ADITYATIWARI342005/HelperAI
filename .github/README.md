### Activity Logs (`data/logs/`)
- Daily log files: `activity_YYYY-MM-DD.log`
- Contains timestamps and random development activities
- Examples: "Code review and optimization", "Bug fixes and improvements"

### Statistics (`data/stats/`)
- `repository_stats.json` - Tracks daily commit metrics
- Includes: commits count, lines added/removed, files changed
- Auto-cleanup after 30 days

### Files Not Being Committed
1. Ensure `.gitignore` allows `data/` directory
2. Check workflow has proper permissions
3. Verify Git configuration in workflow
