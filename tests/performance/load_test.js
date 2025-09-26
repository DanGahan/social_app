/**
 * Load Testing Script for Social App API
 *
 * Tests API endpoints under various load conditions to ensure
 * performance targets are met (< 200ms for 95th percentile).
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const loginFailureRate = new Rate('login_failures');
const postCreationTrend = new Trend('post_creation_duration');
const likeToggleCounter = new Counter('like_toggle_requests');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 100 },    // Ramp up to 100 users
    { duration: '5m', target: 100 },    // Stay at 100 users
    { duration: '2m', target: 200 },    // Ramp up to 200 users
    { duration: '5m', target: 200 },    // Stay at 200 users
    { duration: '2m', target: 0 },      // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<200'],   // 95% of requests under 200ms
    http_req_failed: ['rate<0.01'],     // Error rate under 1%
    login_failures: ['rate<0.05'],      // Login failure rate under 5%
  },
};

// Test data
const baseUrl = __ENV.API_BASE_URL || 'http://localhost:5000';
const testUsers = [
  { email: 'user1@example.com', password: 'testpassword' },
  { email: 'user2@example.com', password: 'testpassword' },
  { email: 'user3@example.com', password: 'testpassword' },
  // Add more test users as needed
];

/**
 * Main test function executed by each virtual user
 */
export default function () {
  const user = testUsers[Math.floor(Math.random() * testUsers.length)];

  group('Authentication Flow', () => {
    testUserLogin(user);
  });

  group('Post Operations', () => {
    testGetPosts();
    testCreatePost();
  });

  group('Social Interactions', () => {
    testLikePost();
    testGetComments();
    testAddComment();
  });

  sleep(1); // Think time between iterations
}

/**
 * Test user login performance
 */
function testUserLogin(user) {
  const loginPayload = JSON.stringify({
    email: user.email,
    password: user.password,
  });

  const loginParams = {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: { name: 'login' },
  };

  const loginResponse = http.post(
    `${baseUrl}/auth/login`,
    loginPayload,
    loginParams
  );

  const loginSuccess = check(loginResponse, {
    'login status is 200': (r) => r.status === 200,
    'login response time < 500ms': (r) => r.timings.duration < 500,
    'login returns token': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.token !== undefined;
      } catch {
        return false;
      }
    },
  });

  loginFailureRate.add(!loginSuccess);

  if (loginSuccess && loginResponse.status === 200) {
    const body = JSON.parse(loginResponse.body);
    return {
      token: body.token,
      userId: body.user_id,
    };
  }

  return null;
}

/**
 * Test getting user posts performance
 */
function testGetPosts() {
  const auth = testUserLogin(testUsers[0]); // Use first test user
  if (!auth) return;

  const getPostsParams = {
    headers: {
      'x-access-token': auth.token,
    },
    tags: { name: 'get_posts' },
  };

  const response = http.get(
    `${baseUrl}/users/${auth.userId}/posts`,
    getPostsParams
  );

  check(response, {
    'get posts status is 200': (r) => r.status === 200,
    'get posts response time < 300ms': (r) => r.timings.duration < 300,
    'get posts returns array': (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body);
      } catch {
        return false;
      }
    },
  });
}

/**
 * Test post creation performance
 */
function testCreatePost() {
  const auth = testUserLogin(testUsers[0]);
  if (!auth) return;

  const postPayload = JSON.stringify({
    image_url: `/uploads/test_image_${Date.now()}.jpg`,
    caption: `Load test post created at ${new Date().toISOString()}`,
  });

  const createParams = {
    headers: {
      'Content-Type': 'application/json',
      'x-access-token': auth.token,
    },
    tags: { name: 'create_post' },
  };

  const response = http.post(
    `${baseUrl}/posts`,
    postPayload,
    createParams
  );

  const success = check(response, {
    'create post status is 201': (r) => r.status === 201,
    'create post response time < 400ms': (r) => r.timings.duration < 400,
    'create post returns post_id': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.post_id !== undefined;
      } catch {
        return false;
      }
    },
  });

  if (success && response.status === 201) {
    postCreationTrend.add(response.timings.duration);
  }
}

/**
 * Test like toggle performance
 */
function testLikePost() {
  const auth = testUserLogin(testUsers[0]);
  if (!auth) return;

  // Use a known post ID (would need to be set up in test data)
  const postId = 1;

  const likeParams = {
    headers: {
      'x-access-token': auth.token,
    },
    tags: { name: 'like_post' },
  };

  const response = http.post(
    `${baseUrl}/posts/${postId}/like`,
    null,
    likeParams
  );

  const success = check(response, {
    'like toggle status is 200': (r) => r.status === 200,
    'like toggle response time < 200ms': (r) => r.timings.duration < 200,
    'like toggle returns action': (r) => {
      try {
        const body = JSON.parse(r.body);
        return ['liked', 'unliked'].includes(body.action);
      } catch {
        return false;
      }
    },
  });

  likeToggleCounter.add(1);
}

/**
 * Test get comments performance
 */
function testGetComments() {
  const auth = testUserLogin(testUsers[0]);
  if (!auth) return;

  const postId = 1;

  const commentsParams = {
    headers: {
      'x-access-token': auth.token,
    },
    tags: { name: 'get_comments' },
  };

  const response = http.get(
    `${baseUrl}/posts/${postId}/comments?page=1&per_page=10`,
    commentsParams
  );

  check(response, {
    'get comments status is 200': (r) => r.status === 200,
    'get comments response time < 300ms': (r) => r.timings.duration < 300,
    'get comments returns structure': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.comments !== undefined && body.pagination !== undefined;
      } catch {
        return false;
      }
    },
  });
}

/**
 * Test add comment performance
 */
function testAddComment() {
  const auth = testUserLogin(testUsers[0]);
  if (!auth) return;

  const postId = 1;
  const commentPayload = JSON.stringify({
    content: `Load test comment created at ${Date.now()}`,
  });

  const commentParams = {
    headers: {
      'Content-Type': 'application/json',
      'x-access-token': auth.token,
    },
    tags: { name: 'add_comment' },
  };

  const response = http.post(
    `${baseUrl}/posts/${postId}/comments`,
    commentPayload,
    commentParams
  );

  check(response, {
    'add comment status is 201': (r) => r.status === 201,
    'add comment response time < 400ms': (r) => r.timings.duration < 400,
    'add comment returns comment': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.comment !== undefined && body.comment.id !== undefined;
      } catch {
        return false;
      }
    },
  });
}

/**
 * Setup function - runs once before all tests
 */
export function setup() {
  console.log('Starting load test setup...');

  // Verify API is accessible
  const healthCheck = http.get(`${baseUrl}/`);
  if (healthCheck.status !== 200) {
    throw new Error(`API not accessible at ${baseUrl}`);
  }

  console.log('Load test setup complete');
  return { baseUrl };
}

/**
 * Teardown function - runs once after all tests
 */
export function teardown(data) {
  console.log('Load test completed');
  console.log(`Tested against: ${data.baseUrl}`);
}
