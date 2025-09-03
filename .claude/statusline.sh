#!/bin/bash
# Enhanced Claude Code statusline with context tracking, cost info, and session details
input=$(cat)

# Extract basic values using jq with safe defaults
MODEL_DISPLAY=$(echo "$input" | jq -r '.model.display_name // "Claude"')
PROJECT_DIR=$(echo "$input" | jq -r '.workspace.project_dir // ""')
CURRENT_DIR=$(echo "$input" | jq -r '.workspace.current_dir // ""')

# Extract cost and metrics information
TOTAL_COST=$(echo "$input" | jq -r '.cost.total_cost_usd // 0')
TOTAL_DURATION=$(echo "$input" | jq -r '.cost.total_duration_ms // 0')
LINES_ADDED=$(echo "$input" | jq -r '.cost.total_lines_added // 0')
LINES_REMOVED=$(echo "$input" | jq -r '.cost.total_lines_removed // 0')

# Git branch detection
GIT_BRANCH=""
if git rev-parse --git-dir > /dev/null 2>&1; then
    BRANCH=$(git branch --show-current 2>/dev/null)
    if [ -n "$BRANCH" ]; then
        GIT_BRANCH=" | 🌿 $BRANCH "
    fi
fi

# Context estimation (rough approximation based on activity)
# Claude models typically have ~200K token context windows
CONTEXT_LIMIT=200000
# Estimate tokens based on duration (1 token per 100ms) + line changes (4 tokens per line)
ESTIMATED_TOKENS=$(( (TOTAL_DURATION / 100) + (LINES_ADDED * 4) + (LINES_REMOVED * 2) ))
if [ $ESTIMATED_TOKENS -gt $CONTEXT_LIMIT ]; then
    ESTIMATED_TOKENS=$CONTEXT_LIMIT
fi

CONTEXT_REMAINING=$((CONTEXT_LIMIT - ESTIMATED_TOKENS))
CONTEXT_PCT=$((CONTEXT_REMAINING * 100 / CONTEXT_LIMIT))

# Estimate time until context reset (assuming 1000 tokens per minute of active use)
MINUTES_REMAINING=$((CONTEXT_REMAINING / 1000))
HOURS=$((MINUTES_REMAINING / 60))
MINS=$((MINUTES_REMAINING % 60))

# Format cost display
if (( $(echo "$TOTAL_COST < 0.01" | bc -l 2>/dev/null || echo "1") )); then
    COST_DISPLAY=$(printf "%.4f" "$TOTAL_COST")
else
    COST_DISPLAY=$(printf "%.2f" "$TOTAL_COST")
fi

# Format session duration
DURATION_SEC=$((TOTAL_DURATION / 1000))
DURATION_MIN=$((DURATION_SEC / 60))
DURATION_HOURS=$((DURATION_MIN / 60))
if [ $DURATION_HOURS -gt 0 ]; then
    DURATION_DISPLAY="${DURATION_HOURS}h $((DURATION_MIN % 60))m"
elif [ $DURATION_MIN -gt 0 ]; then
    DURATION_DISPLAY="${DURATION_MIN}m"
else
    DURATION_DISPLAY="${DURATION_SEC}s"
fi

# Color coding for context remaining
if [ $CONTEXT_PCT -gt 50 ]; then
    CONTEXT_COLOR="\033[32m"  # Green
elif [ $CONTEXT_PCT -gt 20 ]; then
    CONTEXT_COLOR="\033[33m"  # Yellow
else
    CONTEXT_COLOR="\033[31m"  # Red
fi
RESET_COLOR="\033[0m"  # Reset color

# Additional subtle colors for different info types
TIME_COLOR="\033[36m"      # Cyan for time information
COST_COLOR="\033[33m"      # Yellow for cost/financial
METRIC_COLOR="\033[35m"    # Magenta for metrics/tokens

# Format directory display
PROJECT_NAME="${PROJECT_DIR##*/}"
CURRENT_NAME="${CURRENT_DIR##*/}"
if [ "$PROJECT_NAME" = "$CURRENT_NAME" ] || [ -z "$PROJECT_NAME" ]; then
    DIR_DISPLAY="📁 $CURRENT_NAME"
else
    DIR_DISPLAY="🎯 $PROJECT_NAME: 📁 $CURRENT_NAME"
fi

# Time until reset display
if [ $HOURS -gt 0 ]; then
    RESET_TIME="${HOURS}h ${MINS}m"
else
    RESET_TIME="${MINS}m"
fi

# Calculate actual reset time
CURRENT_EPOCH=$(date +%s)
RESET_EPOCH=$((CURRENT_EPOCH + (MINUTES_REMAINING * 60)))
# Handle both macOS (date -r) and Linux (date -d) formats
RESET_TIME_DISPLAY=$(date -r $RESET_EPOCH +"%H:%M" 2>/dev/null || date -d "@$RESET_EPOCH" +"%H:%M" 2>/dev/null || echo "??:??")

# Calculate cost per hour if duration is significant
COST_PER_HOUR=""
if [ $DURATION_MIN -gt 0 ]; then
    HOURS_DECIMAL=$(echo "scale=2; $DURATION_MIN / 60" | bc -l 2>/dev/null || echo "0")
    if (( $(echo "$HOURS_DECIMAL > 0" | bc -l 2>/dev/null || echo "0") )); then
        HOURLY_RATE=$(echo "scale=2; $TOTAL_COST / $HOURS_DECIMAL" | bc -l 2>/dev/null || echo "0")
        if (( $(echo "$HOURLY_RATE > 0" | bc -l 2>/dev/null || echo "0") )); then
            COST_PER_HOUR=" (\$${HOURLY_RATE}/h)"
        fi
    fi
fi

# Calculate tokens per minute if duration is significant
TPM=""
if [ $DURATION_MIN -gt 0 ] && [ $ESTIMATED_TOKENS -gt 0 ]; then
    TOKENS_PER_MIN=$((ESTIMATED_TOKENS / DURATION_MIN))
    TPM=" (${TOKENS_PER_MIN} tpm)"
fi

# Build two-line status display
# Line 1: Keep original format with project/directory info
echo "[$MODEL_DISPLAY] 🎯 ${PROJECT_DIR##*/}: 📁 ${CURRENT_DIR##*/}${GIT_BRANCH}"
# Line 2: Enhanced with reset time, cost per hour, and tokens per minute with subtle colors
echo -e "🧠 ${CONTEXT_COLOR}Context Remaining: ${CONTEXT_PCT}% ${TIME_COLOR}(⏳ ~${RESET_TIME} until reset @ ${RESET_TIME_DISPLAY}) ${COST_COLOR}💰 \$${COST_DISPLAY}${COST_PER_HOUR} 📊 ${METRIC_COLOR}${ESTIMATED_TOKENS} tok${TPM}${RESET_COLOR}"