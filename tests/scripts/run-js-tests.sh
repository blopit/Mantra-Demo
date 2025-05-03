#!/bin/bash
# Consolidated test runner for JavaScript/Playwright tests

# Function to find an available port
find_available_port() {
    local port=9323
    while nc -z localhost $port 2>/dev/null; do
        ((port++))
    done
    echo $port
}

# Parse command line arguments
REPORTER="html"
SHOW_REPORT=true
TEST_PATH=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-report)
            SHOW_REPORT=false
            shift
            ;;
        --reporter=*)
            REPORTER="${1#*=}"
            shift
            ;;
        --path=*)
            TEST_PATH="${1#*=}"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--no-report] [--reporter=html|dot|line|list] [--path=path/to/tests]"
            exit 1
            ;;
    esac
done

# Build the command
CMD="npx playwright test"
if [ -n "$TEST_PATH" ]; then
    CMD="$CMD $TEST_PATH"
fi
CMD="$CMD --reporter=$REPORTER"

# Run the tests
echo "Running: $CMD"
eval $CMD
TEST_EXIT_CODE=$?

# Only show report if tests were run and report viewing is enabled
if [ "$SHOW_REPORT" = true ] && [ -d "playwright-report" ]; then
    # Find an available port
    PORT=$(find_available_port)
    
    # Start the report server in background
    npx playwright show-report --port $PORT &
    REPORT_PID=$!
    
    # Wait for the server to start
    echo "Waiting for report server to start on port $PORT..."
    while ! nc -z localhost $PORT 2>/dev/null; do
        sleep 0.1
    done
    
    # Open the report in the default browser
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "http://localhost:$PORT"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open "http://localhost:$PORT"
    elif [[ "$OSTYPE" == "msys" ]]; then
        start "http://localhost:$PORT"
    fi
    
    # Wait for user input
    read -p "Press Enter to close the report server..."
    
    # Kill the report server gracefully
    if kill -0 $REPORT_PID 2>/dev/null; then
        kill $REPORT_PID
        wait $REPORT_PID 2>/dev/null
    fi
fi

# Exit with the test exit code
exit $TEST_EXIT_CODE
