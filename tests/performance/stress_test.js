/**
 * Stress Testing Script for Social App API
 *
 * Tests system behavior under extreme load conditions.
 * Identifies breaking point and recovery behavior.
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter, Gauge } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const responseTime = new Trend('response_time');
const activeUsers = new Gauge('active_users');
const failedRequests = new Counter('failed_requests');

// Stress test configuration
export const options = {
  stages: [
    // Gradual ramp up to find breaking point
    { duration: '1m', target: 50 },     // Warm up
    { duration: '2m', target: 100 },    // Normal load
    { duration: '2m', target: 200 },    // High load
    { duration: '2m', target: 400 },    // Very high load
    { duration: '2m', target: 800 },    // Extreme load
    { duration: '3m', target: 1200 },   // Breaking point
    { duration: '2m', target: 400 },    // Recovery test
    { duration: '2m', target: 100 },    // Return to normal
    { duration: '1m', target: 0 },      // Cool down
  ],
  thresholds: {
    errors: ['rate<0.1'], // Error rate should be below 10% even under stress
    response_time: ['p(95)<2000'], // 95th percentile under 2s under stress
  },
};

const baseUrl = __ENV.API_BASE_URL || 'http://localhost:5000';

export default function () {
  activeUsers.add(1);

  group('Stress Test - Authentication', () => {
    stressTestLogin();
  });

  group('Stress Test - High Frequency Operations', () => {
    stressTestLikeToggle();
    stressTestCommentCreation();
  });

  group('Stress Test - Data Intensive Operations', () => {
    stressTestPostRetrieval();
    stressTestPostCreation();
  });

  // Reduced think time to increase load
  sleep(0.1);
}

function stressTestLogin() {
  const payload = JSON.stringify({
    email: 'user' + Math.floor(Math.random() * 1000) + '@example.com',
    password: 'testpassword',
  });

  const params = {
    headers: { 'Content-Type': 'application/json' },
    timeout: '10s', // Longer timeout for stress conditions
  };

  const response = http.post(baseUrl + '/auth/login', payload, params);

  const success = check(response, {
    'login completed': (r) => r.status !== 0, // Any response (even error) is better than timeout
    'login response time acceptable': (r) => r.timings.duration < 5000,
  });

  if (!success) {
    failedRequests.add(1);
    errorRate.add(1);
  } else {
    errorRate.add(0);
    responseTime.add(response.timings.duration);
  }

  return response.status === 200 ? JSON.parse(response.body) : null;
}

function stressTestLikeToggle() {
  const auth = stressTestLogin();
  if (!auth || !auth.token) return;

  const postId = Math.floor(Math.random() * 10) + 1; // Random post ID 1-10

  const params = {
    headers: { 'x-access-token': auth.token },
    timeout: '5s',
  };

  const response = http.post(baseUrl + '/posts/' + postId + '/like', null, params);

  const success = check(response, {
    'like toggle completed': (r) => r.status !== 0,
    'like toggle response time acceptable': (r) => r.timings.duration < 3000,
  });

  if (!success) {
    failedRequests.add(1);
    errorRate.add(1);
  } else {
    errorRate.add(0);
    responseTime.add(response.timings.duration);
  }
}

function stressTestCommentCreation() {
  const auth = stressTestLogin();
  if (!auth || !auth.token) return;

  const postId = Math.floor(Math.random() * 10) + 1;
  const payload = JSON.stringify({
    content: 'Stress test comment ' + Date.now() + ' ' + Math.random(),
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'x-access-token': auth.token,
    },
    timeout: '10s',
  };

  const response = http.post(
    baseUrl + '/posts/' + postId + '/comments',
    payload,
    params
  );

  const success = check(response, {
    'comment creation completed': (r) => r.status !== 0,
    'comment creation response time acceptable': (r) => r.timings.duration < 5000,
  });

  if (!success) {
    failedRequests.add(1);
    errorRate.add(1);
  } else {
    errorRate.add(0);
    responseTime.add(response.timings.duration);
  }
}

function stressTestPostRetrieval() {
  const auth = stressTestLogin();
  if (!auth || !auth.token) return;

  const userId = Math.floor(Math.random() * 100) + 1; // Random user ID

  const params = {
    headers: { 'x-access-token': auth.token },
    timeout: '10s',
  };

  const response = http.get(baseUrl + '/users/' + userId + '/posts', params);

  const success = check(response, {
    'post retrieval completed': (r) => r.status !== 0,
    'post retrieval response time acceptable': (r) => r.timings.duration < 8000,
  });

  if (!success) {
    failedRequests.add(1);
    errorRate.add(1);
  } else {
    errorRate.add(0);
    responseTime.add(response.timings.duration);
  }
}

function stressTestPostCreation() {
  const auth = stressTestLogin();
  if (!auth || !auth.token) return;

  const payload = JSON.stringify({
    image_url: '/uploads/stress_test_' + Date.now() + '_' + Math.random() + '.jpg',
    caption: 'Stress test post created at ' + new Date().toISOString() + ' by user ' + Math.random(),
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'x-access-token': auth.token,
    },
    timeout: '15s', // Longer timeout for creation operations
  };

  const response = http.post(baseUrl + '/posts', payload, params);

  const success = check(response, {
    'post creation completed': (r) => r.status !== 0,
    'post creation response time acceptable': (r) => r.timings.duration < 10000,
  });

  if (!success) {
    failedRequests.add(1);
    errorRate.add(1);
  } else {
    errorRate.add(0);
    responseTime.add(response.timings.duration);
  }
}

export function setup() {
  console.log('🔥 Starting stress test...');
  console.log('Target API: ' + baseUrl);
  console.log('This test will gradually increase load to find breaking points');

  // Verify API accessibility
  const healthCheck = http.get(baseUrl + '/', { timeout: '30s' });
  if (healthCheck.status !== 200 && healthCheck.status !== 404) {
    throw new Error('API not accessible at ' + baseUrl + '. Status: ' + healthCheck.status);
  }

  return { startTime: Date.now() };
}

export function teardown(data) {
  const duration = (Date.now() - data.startTime) / 1000;
  console.log('\n🏁 Stress test completed in ' + duration + 's');
  console.log('📊 Check the metrics above for breaking point analysis');
  console.log('🔍 Look for:');
  console.log('  - When error rate started increasing significantly');
  console.log('  - Response time degradation patterns');
  console.log('  - System recovery behavior after load reduction');
}
