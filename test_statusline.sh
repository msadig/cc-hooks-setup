#!/bin/bash
# Test script for the 5-hour session window calculation

# Create a test transcript file with a timestamp
TEST_TRANSCRIPT="/tmp/test_transcript.jsonl"

# Get current time and calculate times for testing
CURRENT_EPOCH=$(date +%s)

# Test Case 1: Session started 2 hours ago (should show ~3h remaining)
TWO_HOURS_AGO=$((CURRENT_EPOCH - 7200))
if date --version >/dev/null 2>&1; then
    # Linux
    TWO_HOURS_AGO_ISO=$(date -u -d "@$TWO_HOURS_AGO" +"%Y-%m-%dT%H:%M:%S.000Z")
else
    # macOS
    TWO_HOURS_AGO_ISO=$(date -u -r $TWO_HOURS_AGO +"%Y-%m-%dT%H:%M:%S.000Z")
fi

echo "Creating test transcript with session started 2 hours ago..."
echo '{"timestamp": "'$TWO_HOURS_AGO_ISO'", "type": "user", "message": {"content": "test"}}' > $TEST_TRANSCRIPT

# Source the statusline function
source .claude/statusline.sh

# Test the function
echo "Test Case 1: Session started 2 hours ago"
echo "Expected: ~3h remaining"
echo -n "Result: "
TRANSCRIPT_PATH=$TEST_TRANSCRIPT
SESSION_RESET_INFO=$(get_session_window_reset "$TRANSCRIPT_PATH")
echo "Session expires in ${SESSION_RESET_INFO%|*} @ ${SESSION_RESET_INFO#*|}"
echo ""

# Test Case 2: Session started 4.5 hours ago (should show ~30m remaining)
FOUR_HALF_HOURS_AGO=$((CURRENT_EPOCH - 16200))
if date --version >/dev/null 2>&1; then
    # Linux
    FOUR_HALF_HOURS_AGO_ISO=$(date -u -d "@$FOUR_HALF_HOURS_AGO" +"%Y-%m-%dT%H:%M:%S.000Z")
else
    # macOS
    FOUR_HALF_HOURS_AGO_ISO=$(date -u -r $FOUR_HALF_HOURS_AGO +"%Y-%m-%dT%H:%M:%S.000Z")
fi

echo '{"timestamp": "'$FOUR_HALF_HOURS_AGO_ISO'", "type": "user", "message": {"content": "test"}}' > $TEST_TRANSCRIPT

echo "Test Case 2: Session started 4.5 hours ago"
echo "Expected: ~30m remaining"
echo -n "Result: "
SESSION_RESET_INFO=$(get_session_window_reset "$TRANSCRIPT_PATH")
echo "Session expires in ${SESSION_RESET_INFO%|*} @ ${SESSION_RESET_INFO#*|}"
echo ""

# Test Case 3: Session started 6 hours ago (should show expired)
SIX_HOURS_AGO=$((CURRENT_EPOCH - 21600))
if date --version >/dev/null 2>&1; then
    # Linux
    SIX_HOURS_AGO_ISO=$(date -u -d "@$SIX_HOURS_AGO" +"%Y-%m-%dT%H:%M:%S.000Z")
else
    # macOS
    SIX_HOURS_AGO_ISO=$(date -u -r $SIX_HOURS_AGO +"%Y-%m-%dT%H:%M:%S.000Z")
fi

echo '{"timestamp": "'$SIX_HOURS_AGO_ISO'", "type": "user", "message": {"content": "test"}}' > $TEST_TRANSCRIPT

echo "Test Case 3: Session started 6 hours ago"
echo "Expected: expired"
echo -n "Result: "
SESSION_RESET_INFO=$(get_session_window_reset "$TRANSCRIPT_PATH")
echo "Session expires in ${SESSION_RESET_INFO%|*} @ ${SESSION_RESET_INFO#*|}"
echo ""

# Clean up
rm -f $TEST_TRANSCRIPT

echo "Test completed!"