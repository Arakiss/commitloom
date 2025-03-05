# CommitLoom Usage Metrics

CommitLoom now includes comprehensive usage metrics to help you understand your usage patterns, track costs, and measure productivity improvements.

## Introduction

The metrics system is designed to be:
- **Private**: All data is stored locally; nothing is sent to external servers
- **Transparent**: Clear data collection with easy access to view your metrics
- **Useful**: Provides insights about cost savings, time saved, and usage patterns

## Available Metrics

CommitLoom tracks the following metrics:

### Basic Metrics
- Total commits generated
- Total tokens used
- Total cost in EUR
- Total files processed
- Estimated time saved

### Repository Metrics
- Most active repositories
- Usage frequency by repository
- File changes by repository

### Model Usage Metrics
- Token usage by model
- Cost breakdown by model
- Efficiency metrics (tokens per commit, cost per file)

### Processing Metrics
- Batch vs. single commits
- Average processing time
- Success rates

## Viewing Metrics

To view your metrics, use the `stats` command:

```bash
loom stats
```

This will display a summary of your usage statistics. To see more detailed information, you can use the debug flag:

```bash
loom stats -d
```

## Data Storage

Metrics are stored locally in the following location, based on your operating system:

- **Linux**: `~/.local/share/commitloom/metrics/`
- **macOS**: `~/Library/Application Support/commitloom/metrics/`
- **Windows**: `%APPDATA%\commitloom\metrics\`

The data is stored in two JSON files:
- `commit_metrics.json`: Contains detailed information about each commit
- `usage_statistics.json`: Contains aggregated statistics about your usage

## Privacy

CommitLoom respects your privacy:
- No telemetry or data collection occurs without your knowledge
- All metrics are stored locally on your machine
- No data is ever sent to external servers
- You can delete the metrics files at any time to reset your statistics

## How Time Savings Are Calculated

CommitLoom estimates time savings based on the assumption that writing a quality commit message manually takes approximately 3 minutes on average. The time saved is calculated as:

```
time_saved = estimated_manual_time - actual_processing_time
```

Where:
- `estimated_manual_time` is 3 minutes (180 seconds)
- `actual_processing_time` is the time taken by CommitLoom to generate the commit message

This provides a conservative estimate of how much time you're saving by using CommitLoom.

## Future Enhancements

In future versions, we plan to enhance the metrics system with:
- Interactive visualizations
- Export capabilities (CSV, JSON)
- More detailed analysis by file type
- Team-based aggregated statistics (while maintaining privacy)
- Integration with development workflows and productivity tools