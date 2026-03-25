// PostHog analytics disabled for self-hosted mode
// This file is kept for compatibility but PostHog is not initialized in self-hosted deployments

import posthog from 'posthog-js';

// Only initialize PostHog if NOT in self-hosted local mode
if (process.env.NEXT_PUBLIC_POSTHOG_KEY && process.env.NEXT_PUBLIC_ENV_MODE !== 'LOCAL') {
  posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY, {
    api_host: '/ingest',
    ui_host: 'https://eu.posthog.com',
    defaults: '2025-05-24',
    capture_exceptions: true, // This enables capturing exceptions using Error Tracking, set to false if you don't want this
    debug: process.env.NODE_ENV === 'development',
  });
}
