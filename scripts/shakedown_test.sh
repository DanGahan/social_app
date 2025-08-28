#!/bin/bash

set -e # Exit immediately if a command exits with a non-zero status.

echo "--- Starting Shakedown Test ---"

# Function to run a test step and report its status
run_test_step() {
    local step_name="$1"
    local command="$2"
    local success_message="$3"
    local failure_message="$4"

    echo "$step_name"
    if eval "$command"; then
        echo "$success_message"
    else
        echo "$failure_message"
        exit 1 # Exit on first failure
    fi
}

run_test_step "1. Bringing down existing Docker containers..." \
    "docker-compose down" \
    "1. Bringing down existing Docker containers: PASSED" \
    "1. Bringing down existing Docker containers: FAILED"

run_test_step "2. Rebuilding Docker images..." \
    "docker-compose build" \
    "2. Rebuilding Docker images: PASSED" \
    "2. Rebuilding Docker images: FAILED"

run_test_step "3. Starting Docker containers in detached mode..." \
    "docker-compose up -d" \
    "3. Starting Docker containers in detached mode: PASSED" \
    "3. Starting Docker containers in detached mode: FAILED"

run_test_step "4. Waiting for services to become healthy..." \
    "sleep 20" \
    "4. Waiting for services to become healthy: PASSED" \
    "4. Waiting for services to become healthy: FAILED"

run_test_step "5. Waiting for 'users' table to be created..." \
    "TIMEOUT=60; while ! docker-compose exec db psql -U user -d social_db -c '\dt' | grep -q \" users \"; do sleep 5; TIMEOUT=$((TIMEOUT-5)); if [ $TIMEOUT -le 0 ]; then echo \"Timeout waiting for 'users' table!\"; exit 1; fi; done" \
    "5. 'users' table created: PASSED" \
    "5. 'users' table created: FAILED"

# 6. DB Table Presence Check...
echo "6. DB Table Presence Check..."

# Get just the list of table names
TABLES=$(docker-compose exec -T db psql -U user -d social_db -Atc "SELECT tablename FROM pg_tables WHERE schemaname='public';")

EXPECTED_TABLES="posts connections connection_requests users"
DB_CHECK_STATUS="PASSED"

for table in $EXPECTED_TABLES; do
    if ! echo "$TABLES" | grep -qw "$table"; then
        echo "DB Table Check: FAILED (Table $table not found)"
        DB_CHECK_STATUS="FAILED"
        break
    fi
done

echo "6. DB Table Presence Check: $DB_CHECK_STATUS"
if [ "$DB_CHECK_STATUS" = "FAILED" ]; then
    exit 1
fi

run_test_step "7. Populating the database..." \
    "docker-compose exec backend python populate_db.py" \
    "7. Populating the database: PASSED" \
    "7. Populating the database: FAILED"

# 8. Populated Data Verification (User Count, Profile Pic, Posts)...
echo "8. Populated Data Verification (User Count, Profile Pic, Posts)..."
USER_COUNT=$(docker-compose exec backend python -c "from models import User; from app import session; print(session.query(User).count())")
if [ "$USER_COUNT" -eq 20 ]; then
    echo "User Count Check: PASSED (Found 20 users)"
else
    echo "User Count Check: FAILED (Expected 20 users, found $USER_COUNT)"
    exit 1
fi

PROFILE_PIC_URL=$(docker-compose exec backend python -c "from models import User; from app import session; user = session.query(User).filter_by(email='user1@example.com').first(); print(user.profile_picture_url if user else '')")
if [ -n "$PROFILE_PIC_URL" ]; then
    echo "Profile Picture URL Check: PASSED (User1 has a profile picture URL)"
else
    echo "Profile Picture URL Check: FAILED (User1 does not have a profile picture URL)"
    exit 1
fi

POST_IMAGE_URLS=$(docker-compose exec backend python -c "from models import User, Post; from app import session; user = session.query(User).filter_by(email='user1@example.com').first(); posts = session.query(Post).filter_by(user_id=user.id).all(); print([p.image_url for p in posts] if posts else [])")
if echo "$POST_IMAGE_URLS" | grep -q "http"; then
    echo "Posts Image URL Check: PASSED (User1 has posts with image URLs)"
else
    echo "Posts Image URL Check: FAILED (User1 has no posts or no image URLs)"
    echo "Response: $POST_IMAGE_URLS"
    exit 1
fi
echo "8. Populated Data Verification: PASSED" # Overall status for step 8

run_test_step "9. Performing Backend Confidence Test (Login)..." \
"BACKEND_LOGIN_RESPONSE=\$(curl -s -X POST -H \"Content-Type: application/json\" \
    -d '{\"email\": \"user1@example.com\", \"password\": \"password1\"}' \
    http://localhost:5001/auth/login) && \
 JWT_TOKEN=\$(echo \"\$BACKEND_LOGIN_RESPONSE\" | python3 -c 'import sys, json; print(json.load(sys.stdin).get(\"token\", \"\"))') && \
 [ -n \"\$JWT_TOKEN\" ]" \
"9. Performing Backend Confidence Test (Login): PASSED" \
"9. Performing Backend Confidence Test (Login): FAILED (No token received or login failed)"

run_test_step "10. Performing Backend GET API Exercise (/users/me)..." \
"USERS_ME_RESPONSE=\$(curl -s -H \"x-access-token: \$JWT_TOKEN\" http://localhost:5001/users/me) && \
 echo \"\$USERS_ME_RESPONSE\" | grep -q \"user_id\" && \
 echo \"\$USERS_ME_RESPONSE\" | grep -q \"email\"" \
"10. Performing Backend GET API Exercise (/users/me): PASSED" \
"10. Performing Backend GET API Exercise (/users/me): FAILED (Expected user data not found)"

# 11. Frontend Confidence Test (Login Page content)
run_test_step '11. Performing Frontend Confidence Test (Login Page content)...' \
'FRONTEND_LOGIN_RESPONSE=$(curl -s -L http://localhost:8000/); echo "$FRONTEND_LOGIN_RESPONSE" | grep -q "<h2>Login</h2>"' \
"11. Performing Frontend Confidence Test (Login Page content): PASSED" \
"11. Performing Frontend Confidence Test (Login Page content): FAILED (Did not find '<h2>Login</h2>' in content)"

# 12. Frontend Static File Check (logo.png)
run_test_step '12. Performing Frontend Static File Check (logo.png)...' \
'HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/static/logo.png); [ "$HTTP_CODE" -eq 200 ]' \
"12. Performing Frontend Static File Check (logo.png): PASSED" \
"12. Performing Frontend Static File Check (logo.png): FAILED (HTTP $HTTP_CODE)"

# 13. Frontend Static File Check (default_profile_pic.png)
run_test_step '13. Performing Frontend Static File Check (default_profile_pic.png)...' \
'HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/static/default_profile_pic.png); [ "$HTTP_CODE" -eq 200 ]' \
"13. Performing Frontend Static File Check (default_profile_pic.png): PASSED" \
"13. Performing Frontend Static File Check (default_profile_pic.png): FAILED (HTTP $HTTP_CODE)"

echo "--- Shakedown Test Complete: ALL PASSED ---"
