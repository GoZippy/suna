#!/bin/bash

# Frontend Test Runner Script
# This script runs the comprehensive frontend test suite

set -e

echo "🧪 Starting Frontend Test Suite..."
echo "=================================="

# Check if we're in the right directory
if [ ! -f "vitest.config.ts" ]; then
    echo "❌ Error: vitest.config.ts not found. Please run this script from the frontend-tests directory."
    exit 1
fi

# Install dependencies if needed
echo "📦 Checking dependencies..."
if [ ! -d "node_modules" ]; then
    echo "Installing test dependencies..."
    npm install --silent
fi

# Run unit tests
echo "🔍 Running unit tests..."
npm run test:unit

# Run component tests
echo "🧩 Running component tests..."
npm run test:components

# Run integration tests
echo "🔗 Running integration tests..."
npm run test:integration

# Run accessibility tests
echo "♿ Running accessibility tests..."
npm run test:a11y

# Generate coverage report
echo "📊 Generating coverage report..."
npm run test:coverage

echo "✅ Frontend test suite completed successfully!"
echo "📈 Coverage report available in coverage/ directory"







