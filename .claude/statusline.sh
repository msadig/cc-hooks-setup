#!/bin/bash
# Enhanced Claude Code statusline with session-specific context tracking

# Check for jq dependency first
if ! command -v jq >/dev/null 2>&1; then
    echo "❌ StatusLine: jq not installed"
    echo "Install: brew install jq (macOS) | apt install jq (Ubuntu) | choco install jq (Windows)"
    exit 0
fi

input=$(cat)

# Extract basic values using jq with safe defaults
MODEL_ID=$(echo "$input" | jq -r '.model.id // ""')
MODEL_DISPLAY=$(echo "$input" | jq -r '.model.display_name // "Claude"')
PROJECT_DIR=$(echo "$input" | jq -r '.workspace.project_dir // ""')
CURRENT_DIR=$(echo "$input" | jq -r '.workspace.current_dir // ""')
TRANSCRIPT_PATH=$(echo "$input" | jq -r '.transcript_path // ""')
SESSION_ID=$(echo "$input" | jq -r '.session_id // ""')

# Extract cost and metrics information (these remain global across sessions)
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

# Determine usable context limit (80% of theoretical before auto-compact)
if [[ "$MODEL_DISPLAY" == *"Sonnet"* ]]; then
    CONTEXT_LIMIT=800000   # 800k usable for 1M Sonnet models
else
    CONTEXT_LIMIT=160000   # 160k usable for 200k models (Opus, etc.)
fi

# Session-specific context calculation from transcript
calculate_session_context() {
    local transcript_path="$1"
    
    # Default fallback values when transcript unavailable
    if [[ -z "$transcript_path" || ! -f "$transcript_path" ]]; then
        echo "17900"  # Reasonable default for new sessions
        return
    fi
    
    # Parse transcript to get actual token usage from most recent main-chain message
    local context_tokens=$(jq -r '
        select(.isSidechain != true) |
        select(.message.usage != null) |
        .message.usage |
        (.input_tokens // 0) + 
        (.cache_read_input_tokens // 0) + 
        (.cache_creation_input_tokens // 0)
    ' "$transcript_path" 2>/dev/null | tail -n 1)
    
    # If no valid token count found, use fallback
    if [[ -z "$context_tokens" || "$context_tokens" == "null" ]]; then
        echo "17900"
    else
        echo "$context_tokens"
    fi
}

# Calculate session-specific context from transcript
SESSION_TOKENS=$(calculate_session_context "$TRANSCRIPT_PATH")
if [ $SESSION_TOKENS -gt $CONTEXT_LIMIT ]; then
    SESSION_TOKENS=$CONTEXT_LIMIT
fi

CONTEXT_REMAINING=$((CONTEXT_LIMIT - SESSION_TOKENS))
CONTEXT_PCT=$((CONTEXT_REMAINING * 100 / CONTEXT_LIMIT))

# Context limit warning thresholds (Claude auto-compacts at 95%)
COMPACT_THRESHOLD=95
WARNING_THRESHOLD=80

# Calculate context usage percentage
CONTEXT_USED_PCT=$((SESSION_TOKENS * 100 / CONTEXT_LIMIT))

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

# Color coding based on context usage (not remaining)
if [ $CONTEXT_USED_PCT -lt $WARNING_THRESHOLD ]; then
    CONTEXT_COLOR="\033[32m"  # Green - safe usage
elif [ $CONTEXT_USED_PCT -lt $COMPACT_THRESHOLD ]; then
    CONTEXT_COLOR="\033[33m"  # Yellow - approaching auto-compact
else
    CONTEXT_COLOR="\033[31m"  # Red - will auto-compact soon
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

# Context status message
if [ $CONTEXT_USED_PCT -ge $COMPACT_THRESHOLD ]; then
    CONTEXT_STATUS="auto-compact soon"
elif [ $CONTEXT_USED_PCT -ge $WARNING_THRESHOLD ]; then
    CONTEXT_STATUS="approaching limit"
else
    CONTEXT_STATUS="healthy"
fi

# 5-hour session window calculation
get_session_window_reset() {
    local transcript_path="$1"
    
    if [[ -z "$transcript_path" || ! -f "$transcript_path" ]]; then
        echo "unknown|--:--"
        return
    fi
    
    # Get first message timestamp (session start)
    local session_start=$(jq -r '.timestamp // empty' "$transcript_path" 2>/dev/null | head -n 1)
    
    if [[ -z "$session_start" || "$session_start" == "null" ]]; then
        echo "unknown|--:--"
        return
    fi
    
    # Convert to epoch and add 5 hours
    # Handle both macOS (date -j) and Linux (date -d) formats
    local start_epoch
    if date -d "$session_start" +%s >/dev/null 2>&1; then
        # Linux/GNU date
        start_epoch=$(date -d "$session_start" +%s)
    else
        # macOS date - extract just the date/time part and handle as UTC
        local clean_date="${session_start%%.*}"
        clean_date="${clean_date%%Z}"
        clean_date="${clean_date%%+*}"
        # Use -u flag to interpret as UTC
        start_epoch=$(date -u -j -f "%Y-%m-%dT%H:%M:%S" "$clean_date" +%s 2>/dev/null)
    fi
    
    if [[ -z "$start_epoch" ]]; then
        echo "unknown|--:--"
        return
    fi
    
    local expiry_epoch=$((start_epoch + 18000))  # 5 hours = 18000 seconds
    local current_epoch=$(date +%s)
    
    # Calculate time remaining
    local seconds_remaining=$((expiry_epoch - current_epoch))
    
    if [ $seconds_remaining -le 0 ]; then
        echo "expired|now"
    else
        local hours=$((seconds_remaining / 3600))
        local minutes=$(((seconds_remaining % 3600) / 60))
        local time_display=""
        
        if [ $hours -gt 0 ]; then
            time_display="${hours}h ${minutes}m"
        else
            time_display="${minutes}m"
        fi
        
        # Format reset time for display
        local reset_time
        if date -r $expiry_epoch +"%H:%M" >/dev/null 2>&1; then
            # macOS
            reset_time=$(date -r $expiry_epoch +"%H:%M")
        else
            # Linux
            reset_time=$(date -d "@$expiry_epoch" +"%H:%M")
        fi
        
        echo "$time_display|$reset_time"
    fi
}

# Get session window reset info
SESSION_RESET_INFO=$(get_session_window_reset "$TRANSCRIPT_PATH")
SESSION_RESET_TIME="${SESSION_RESET_INFO%|*}"
SESSION_RESET_AT="${SESSION_RESET_INFO#*|}"

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
if [ $DURATION_MIN -gt 0 ] && [ $SESSION_TOKENS -gt 0 ]; then
    TOKENS_PER_MIN=$((SESSION_TOKENS / DURATION_MIN))
    TPM=" (${TOKENS_PER_MIN} tpm)"
fi

# Format context size for display (200k, 100k, etc)
CONTEXT_DISPLAY=$(( CONTEXT_LIMIT / 1000 ))

# Create a simple progress bar for context usage (shows used, not remaining)
create_progress_bar() {
    local used_percent=$1
    local width=20
    local filled=$(( used_percent * width / 100 ))
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

PROGRESS_BAR=$(create_progress_bar "$CONTEXT_USED_PCT")

# Build two-line status display
# Line 1: Keep original format with project/directory info
echo "[$MODEL_DISPLAY] 🎯 ${PROJECT_DIR##*/}: 📁 ${CURRENT_DIR##*/}${GIT_BRANCH}"
# Line 2: Session context + Session window expiry + Cost info
echo -e "🧠 ${CONTEXT_COLOR}${PROGRESS_BAR} ${CONTEXT_USED_PCT}% of ${CONTEXT_DISPLAY}k (${CONTEXT_STATUS})${RESET_COLOR} ${TIME_COLOR}⏳ Session expires in ${SESSION_RESET_TIME} @ ${SESSION_RESET_AT}${RESET_COLOR} ${COST_COLOR}💰\$${COST_DISPLAY}${COST_PER_HOUR}${RESET_COLOR} ${METRIC_COLOR}📊 ${SESSION_TOKENS} tok${TPM}${RESET_COLOR}"