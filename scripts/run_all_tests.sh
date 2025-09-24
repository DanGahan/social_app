#!/bin/bash

# Comprehensive Test Runner for Social App
# Implements the complete test pyramid as per GitHub issue #31

set -e

echo "🚀 Starting Comprehensive Test Suite - Social App Test Pyramid"
echo "============================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print section headers
print_section() {
    echo -e "\n${BLUE}📋 $1${NC}"
    echo "----------------------------------------"
}

# Function to print results
print_result() {
    if [ $2 -eq 0 ]; then
        echo -e "${GREEN}✅ $1 PASSED${NC}"
    else
        echo -e "${RED}❌ $1 FAILED${NC}"
        return 1
    fi
}

# Initialize results
UNIT_RESULT=0
INTEGRATION_RESULT=0
CONTRACT_RESULT=0
UI_RESULT=0
PERFORMANCE_RESULT=0
SECURITY_RESULT=0

# Start services
print_section "Starting Services"
echo "🐳 Starting Docker services..."
docker-compose up -d
sleep 10

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
timeout 60s bash -c 'until curl -f http://localhost:5000/ > /dev/null 2>&1; do sleep 2; done'
timeout 60s bash -c 'until curl -f http://localhost:8000/ > /dev/null 2>&1; do sleep 2; done'

# 1. UNIT TESTS
print_section "Unit Tests (Base of Pyramid)"

echo "🔧 Running Backend Unit Tests..."
docker-compose exec backend python -m pytest tests/test_*.py -v --cov=. --cov-report=term-missing || UNIT_RESULT=$?

echo "🎨 Running Frontend Unit Tests..."
docker-compose exec frontend python manage.py test || UNIT_RESULT=$((UNIT_RESULT + $?))

print_result "Unit Tests" $UNIT_RESULT

# 2. INTEGRATION TESTS
print_section "Integration Tests (Middle of Pyramid)"

echo "🔗 Running Backend-Database Integration Tests..."
docker-compose exec backend python -m pytest tests/integration/test_database_integration.py -v -m integration || INTEGRATION_RESULT=$?

echo "🌐 Running Frontend-Backend Integration Tests..."
docker-compose exec frontend python -m pytest tests/integration/test_frontend_backend_integration.py -v -m integration || INTEGRATION_RESULT=$((INTEGRATION_RESULT + $?))

print_result "Integration Tests" $INTEGRATION_RESULT

# 3. CONTRACT TESTS
print_section "Contract Tests (API Compatibility)"

echo "📋 Running API Contract Tests..."
docker-compose exec backend python -m pytest tests/contract/test_api_contract.py -v -m contract || CONTRACT_RESULT=$?

echo "📖 Running API Documentation Tests..."
docker-compose exec backend python -m pytest tests/contract/test_api_documentation.py -v || CONTRACT_RESULT=$((CONTRACT_RESULT + $?))

print_result "Contract Tests" $CONTRACT_RESULT

# 4. UI/E2E TESTS (Top of Pyramid)
print_section "UI Functional Tests (Top of Pyramid)"

echo "🎭 Installing Playwright browsers..."
docker-compose exec frontend playwright install --with-deps chromium || true

echo "🖥️ Running UI/E2E Tests..."
docker-compose exec frontend python -m pytest tests/ui/test_user_workflows.py -v -m ui || UI_RESULT=$?

print_result "UI Tests" $UI_RESULT

# 5. PERFORMANCE TESTS
print_section "Performance Tests"

# Check if K6 is available
if command -v k6 >/dev/null 2>&1; then
    echo "⚡ Running Load Tests..."
    API_BASE_URL=http://localhost:5000 k6 run tests/performance/load_test.js || PERFORMANCE_RESULT=$?

    echo "🔥 Running Stress Tests..."
    API_BASE_URL=http://localhost:5000 k6 run tests/performance/stress_test.js || PERFORMANCE_RESULT=$((PERFORMANCE_RESULT + $?))
else
    echo "⚠️ K6 not installed, skipping performance tests"
    echo "Install with: brew install k6 (macOS) or https://k6.io/docs/getting-started/installation/"
    PERFORMANCE_RESULT=0  # Don't fail if K6 not available
fi

print_result "Performance Tests" $PERFORMANCE_RESULT

# 6. STATIC CODE ANALYSIS & SECURITY
print_section "Static Code Analysis & Security"

echo "🔍 Running Backend Security Scan (Bandit)..."
docker-compose exec backend bandit -r . -f json -o bandit-report.json || SECURITY_RESULT=$?
docker-compose exec backend bandit -r . || true  # Show results

echo "🛡️ Running Dependency Security Check (Safety)..."
docker-compose exec backend safety check --json || SECURITY_RESULT=$((SECURITY_RESULT + $?))

echo "📊 Running Code Quality Analysis (Pylint)..."
docker-compose exec backend pylint app.py models.py --output-format=text || SECURITY_RESULT=$((SECURITY_RESULT + $?))

echo "🎨 Running Frontend Security Scan..."
docker-compose exec frontend bandit -r . -f json -o bandit-report.json || SECURITY_RESULT=$((SECURITY_RESULT + $?))
docker-compose exec frontend safety check --json || true

print_result "Security & Code Quality" $SECURITY_RESULT

# GENERATE COMPREHENSIVE REPORT
print_section "Test Results Summary"

TOTAL_RESULT=$((UNIT_RESULT + INTEGRATION_RESULT + CONTRACT_RESULT + UI_RESULT + PERFORMANCE_RESULT + SECURITY_RESULT))

echo "📊 TEST PYRAMID RESULTS:"
echo "========================"
printf "%-20s %s\n" "Unit Tests:" "$([ $UNIT_RESULT -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")"
printf "%-20s %s\n" "Integration Tests:" "$([ $INTEGRATION_RESULT -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")"
printf "%-20s %s\n" "Contract Tests:" "$([ $CONTRACT_RESULT -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")"
printf "%-20s %s\n" "UI Tests:" "$([ $UI_RESULT -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")"
printf "%-20s %s\n" "Performance Tests:" "$([ $PERFORMANCE_RESULT -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")"
printf "%-20s %s\n" "Security Scan:" "$([ $SECURITY_RESULT -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")"

echo ""
if [ $TOTAL_RESULT -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED - Test Pyramid Complete!${NC}"
    echo -e "${GREEN}✅ Code is ready for deployment${NC}"
else
    echo -e "${RED}❌ Some tests failed - Total failures: $TOTAL_RESULT${NC}"
    echo -e "${YELLOW}📋 Review failed tests above and fix before deployment${NC}"
fi

# Test Coverage Summary
print_section "Coverage Analysis"
echo "📈 Generating comprehensive coverage report..."
docker-compose exec backend python -m pytest tests/ --cov=. --cov-report=html --cov-report=term-missing || true

echo ""
echo "🔍 Coverage reports generated:"
echo "  • Backend: backend/htmlcov/index.html"
echo "  • Security: backend/bandit-report.json"

# Cleanup
echo ""
echo "🧹 Test suite complete. Services remain running for debugging."
echo "   Use 'docker-compose down' to stop services when done."

exit $TOTAL_RESULT
