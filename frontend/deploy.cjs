const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const targetRepo = process.env.DEPLOY_REPO || 'git@github.com:theborear/theborear.github.io.git';
const distDir = path.join(__dirname, 'dist');

function run(command, cwd = __dirname) {
  try {
    return execSync(command, { cwd, stdio: 'inherit', env: { ...process.env } });
  } catch (error) {
    console.error(`Command failed: ${command}`);
    process.exit(1);
  }
}

console.log('=== Step 1: Building Frontend ===');
if (process.env.VITE_API_URL) {
  console.log(`Using custom API URL: ${process.env.VITE_API_URL}`);
} else {
  console.log('VITE_API_URL not specified. Frontend will use window.location.origin dynamically.');
}
run('npm run build');

console.log('\n=== Step 2: Preparing Build Directory for Git ===');
if (!fs.existsSync(distDir)) {
  console.error('Error: dist directory does not exist after build!');
  process.exit(1);
}

// Clean any existing local git in dist to prevent history issues
const gitDir = path.join(distDir, '.git');
if (fs.existsSync(gitDir)) {
  fs.rmSync(gitDir, { recursive: true, force: true });
}

// Initialize clean repository
run('git init', distDir);
run('git checkout -b main', distDir);

// Configure local identity for the push commit
run('git config user.name "Eyewear OMS Deployer"', distDir);
run('git config user.email "deployer@eyewear-oms.local"', distDir);

// Add all files
run('git add -A', distDir);

// Commit files
console.log('\n=== Step 3: Committing built files ===');
run('git commit -m "Deploy: Build compiled for theborear.github.io"', distDir);

// Push to target repository
console.log(`\n=== Step 4: Force-pushing to target repository: ${targetRepo} ===`);
try {
  run(`git push -f ${targetRepo} main`, distDir);
  console.log('\n=========================================');
  console.log('🎉 Deployment Completed Successfully!');
  console.log('Your site will be live at: https://theborear.github.io/');
  console.log('=========================================');
} catch (error) {
  console.error('\n❌ Push failed. Please verify:');
  console.log('1. You have write permissions to the repository.');
  console.log('2. Your SSH keys or credentials are set up correctly.');
  process.exit(1);
}
