#!/bin/bash

set -e # Exit immediately if a command exits with a non-zero status. 

echo "--- Starting Shakedown Test ---"

echo "1. Bringing down existing Docker containers..."
docker-compose down

echo "2. Rebuilding Docker images..."
docker-compose build

echo "3. Starting Docker containers in detached mode..."
docker-compose up -d

echo "4. Waiting for services to become healthy..."
# Give services enough time to start and become healthy
sleep 20

echo "5. DB Table Presence Check..."
EXPECTED_TABLES="users posts connections connection_requests"
for table in $EXPECTED_TABLES; 
do
    if ! docker-compose exec db psql -U user -d social_db -c '\dt' | grep -q " $table "; then
        echo "DB Table Check: FAILED (Table $table not found)"
        exit 1
    fi
done
echo "DB Table Check: PASSED (All expected tables found)"

echo "6. Populating the database..."
docker-compose exec backend python populate_db.py

echo "7. Populated Data Verification (User Count, Profile Pic, Posts)..."
USER_COUNT=$(docker-compose exec backend python -c "from models import User; from app import session; print(session.query(User).count())")
if [ "$USER_COUNT" -eq 20 ]; then
    echo "User Count Check: PASSED (Found 20 users)"
else
    echo "User Count Check: FAILED (Expected 20 users, found $USER_COUNT)"
    exit 1
fi

# Verify profile picture URL for user1
PROFILE_PIC_URL=$(docker-compose exec backend python -c "from models import User; from app import session; user = session.query(User).filter_by(email='user1@example.com').first(); print(user.profile_picture_url if user else '')")
if [ -n "$PROFILE_PIC_URL" ]; then
    echo "Profile Picture URL Check: PASSED (User1 has a profile picture URL)"
else
    echo "Profile Picture URL Check: FAILED (User1 does not have a profile picture URL)"
    exit 1
fi

# Verify posts and their image URLs for user1
POST_IMAGE_URLS=$(docker-compose exec backend python -c "from models import User, Post; from app import session; user = session.query(User).filter_by(email='user1@example.com').first(); posts = session.query(Post).filter_by(user_id=user.id).all(); print([p.image_url for p in posts] if posts else [])")

if echo "$POST_IMAGE_URLS" | grep -q "http"; then
    echo "Posts Image URL Check: PASSED (User1 has posts with image URLs)"
else
    echo "Posts Image URL Check: FAILED (User1 has no posts or no image URLs)"
    echo "Response: $POST_IMAGE_URLS"
    exit 1
fi

echo "8. Performing Backend Confidence Test (Login)..."
# populate_db.py creates users with email userX@example.com and password passwordX
BACKEND_LOGIN_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
    -d '{"email": "user1@example.com", "password": "password1"}' \
    http://localhost:5001/auth/login)

JWT_TOKEN=$(echo "$BACKEND_LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))")

if [ -n "$JWT_TOKEN" ]; then
    echo "Backend Login Test: PASSED (Token received)"
else
    echo "Backend Login Test: FAILED (No token received)"
    echo "Response: $BACKEND_LOGIN_RESPONSE"
    exit 1
fi

echo "9. Performing Backend GET API Exercise (/users/me)..."
USERS_ME_RESPONSE=$(curl -s -H "x-access-token: $JWT_TOKEN" http://localhost:5001/users/me)
if echo "$USERS_ME_RESPONSE" | grep -q "user_id" && echo "$USERS_ME_RESPONSE" | grep -q "email"; then
    echo "Backend GET /users/me Test: PASSED (Expected user data found)"
else
    echo "Backend GET /users/me Test: FAILED (Expected user data not found)"
    echo "Response: $USERS_ME_RESPONSE"
    exit 1
fi

echo "10. Performing Frontend Confidence Test (Login Page content)..."
# Use -L to follow redirects, as the root URL redirects to /login/
FRONTEND_LOGIN_RESPONSE=$(curl -s -L http://localhost:8000/)

if echo "$FRONTEND_LOGIN_RESPONSE" | grep -q "<h2>Login</h2>"; then
    echo "Frontend Login Page Test: PASSED (Found '<h2>Login</h2>' in content)"
else
    echo "Frontend Login Page Test: FAILED (Did not find '<h2>Login</h2>' in content)"
    echo "Response: $FRONTEND_LOGIN_RESPONSE"
    exit 1
fi

echo "11. Performing Frontend Static File Check (logo.png)..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/static/logo.png)
if [ "$HTTP_CODE" -eq 200 ]; then
    echo "Frontend Static File Check (logo.png): PASSED (HTTP 200)"
else
    echo "Frontend Static File Check (logo.png): FAILED (HTTP $HTTP_CODE)"
    exit 1
fi

echo "12. Performing Frontend Static File Check (default_profile_pic.png)..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/static/default_profile_pic.png)
if [ "$HTTP_CODE" -eq 200 ]; then
    echo "Frontend Static File Check (default_profile_pic.png): PASSED (HTTP 200)"
else
    echo "Frontend Static File Check (default_profile_pic.png): FAILED (HTTP $HTTP_CODE)"
    exit 1
fi

echo "--- Shakedown Test Complete: ALL PASSED ---"
