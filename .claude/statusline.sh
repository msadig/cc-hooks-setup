#!/bin/bash
# Enhanced Claude Code statusline with context tracking, cost info, and session details
input=$(cat)

# Extract basic values using jq with safe defaults
MODEL_ID=$(echo "$input" | jq -r '.model.id // ""')
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

# Model-specific context limits (in tokens)
# Based on official Claude model specifications
get_context_limit() {
    local model_id="$1"
    
    # Claude Opus 4.1 - 200k context
    if [[ "$model_id" == *"claude-opus-4-1"* ]]; then
        echo 200000
    # Claude 3.5 Sonnet (October 2024) - 200k context
    elif [[ "$model_id" == *"claude-3-5-sonnet"* ]]; then
        echo 200000
    # Claude 3 Opus - 200k context
    elif [[ "$model_id" == *"claude-3-opus"* ]]; then
        echo 200000
    # Claude 3 Haiku - 200k context  
    elif [[ "$model_id" == *"claude-3-haiku"* ]]; then
        echo 200000
    # Claude 2.1 - 200k context
    elif [[ "$model_id" == *"claude-2.1"* ]]; then
        echo 200000
    # Claude 2.0 - 100k context
    elif [[ "$model_id" == *"claude-2.0"* ]]; then
        echo 100000
    # Claude Instant - 100k context
    elif [[ "$model_id" == *"claude-instant"* ]]; then
        echo 100000
    # Default fallback for unknown models
    else
        echo 200000
    fi
}

# Get the context limit for the current model
CONTEXT_LIMIT=$(get_context_limit "$MODEL_ID")

# Improved token estimation algorithm
# More accurate approximation based on Claude's actual tokenization
# Average: ~1.3 tokens per word, ~4 characters per token
# Code tends to have more tokens due to syntax and formatting
calculate_estimated_tokens() {
    local duration="$1"
    local lines_added="$2"
    local lines_removed="$3"
    
    # Base token usage from conversation duration
    # Assuming average interaction generates ~50 tokens per second of API time
    local api_tokens=$(( TOTAL_DURATION / 20 ))
    
    # Code changes: average line has ~10-15 tokens (accounting for syntax, whitespace)
    local code_tokens=$(( (lines_added * 12) + (lines_removed * 8) ))
    
    # Add a baseline for system prompts and context (~2000 tokens overhead)
    local system_overhead=2000
    
    # Total with a multiplier for conversation history (messages accumulate)
    # Each exchange adds previous context, so multiply by a growth factor
    local conversation_multiplier=3
    local total=$(( system_overhead + (api_tokens + code_tokens) * conversation_multiplier ))
    
    echo "$total"
}

# Calculate estimated tokens with improved algorithm
ESTIMATED_TOKENS=$(calculate_estimated_tokens "$TOTAL_DURATION" "$LINES_ADDED" "$LINES_REMOVED")
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

# Format context size for display (200k, 100k, etc)
CONTEXT_DISPLAY=$(( CONTEXT_LIMIT / 1000 ))

# Create a simple progress bar for context usage
create_progress_bar() {
    local percent=$1
    local width=20
    local filled=$(( (100 - percent) * width / 100 ))
    local empty=$(( width - filled ))
    
    local bar="["
    for ((i=0; i<filled; i++)); do
        bar="${bar}█"
    done
    for ((i=0; i<empty; i++)); do
        bar="${bar}░"
    done
    bar="${bar}]"
    
    echo "$bar"
}

PROGRESS_BAR=$(create_progress_bar "$CONTEXT_PCT")

# Build two-line status display
# Line 1: Keep original format with project/directory info
echo "[$MODEL_DISPLAY] 🎯 ${PROJECT_DIR##*/}: 📁 ${CURRENT_DIR##*/}${GIT_BRANCH}"
# Line 2: Enhanced with visual progress bar, model context size, reset time, cost per hour, and tokens per minute
echo -e "🧠 ${CONTEXT_COLOR}${PROGRESS_BAR} ${CONTEXT_PCT}% of ${CONTEXT_DISPLAY}k${RESET_COLOR} ${TIME_COLOR}⏳${RESET_TIME_DISPLAY} ${COST_COLOR}💰\$${COST_DISPLAY}${COST_PER_HOUR} 📊${METRIC_COLOR}${ESTIMATED_TOKENS}tok${TPM}${RESET_COLOR}"