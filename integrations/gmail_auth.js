/**
 * Gmail Browser OAuth Authenticator for Apex Agent
 * Opens Google OAuth in your default browser, captures authorization,
 * and saves tokens locally for autonomous email operations.
 */

const { execSync, spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

console.log('====================================================');
console.log('⚡ Apex Agent — Gmail Browser Authentication Flow');
console.log('====================================================\n');

console.log('Starting Google OAuth browser flow...');
console.log('Your default browser will open. Sign in to your Google Account and click "Allow".\n');

// Launch auto-auth Gmail server
const authProc = spawn('npx', ['-y', '@gongrzhe/server-gmail-autoauth-mcp'], {
  stdio: 'inherit',
  env: process.env
});

authProc.on('error', (err) => {
  console.error('Failed to launch OAuth server:', err.message);
});

authProc.on('close', (code) => {
  console.log(`\nOAuth process completed (code ${code}).`);
});
