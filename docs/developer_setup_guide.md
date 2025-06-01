# Social Download Manager v2.0 - Developer Setup Guide

## Development Environment Setup

This guide will help you set up a complete development environment for contributing to Social Download Manager v2.0.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Development Dependencies](#development-dependencies)
- [Build System](#build-system)
- [Development Workflow](#development-workflow)
- [Debugging and Testing](#debugging-and-testing)
- [Git Workflow](#git-workflow)
- [IDE Configuration](#ide-configuration)

## Prerequisites

### System Requirements
- **Node.js**: v18.0.0 or higher
- **Python**: v3.8.0 or higher
- **Git**: Latest version
- **Operating System**: Windows 10+, macOS 10.14+, or Ubuntu 18.04+

### Required Tools
```bash
# Check versions
node --version    # Should be v18+
python --version  # Should be v3.8+
git --version     # Should be latest

# Additional tools
npm --version     # Comes with Node.js
pip --version     # Comes with Python
```

### Platform-Specific Requirements

**Windows**:
- Visual Studio Build Tools or Visual Studio 2019+
- Windows SDK 10.0.19041.0 or later
- PowerShell 5.1 or PowerShell Core 7+

**macOS**:
- Xcode Command Line Tools: `xcode-select --install`
- Homebrew package manager (recommended)

**Linux**:
- Build essentials: `sudo apt install build-essential`
- Additional dependencies: `sudo apt install libnss3-dev libatk-bridge2.0-dev libgtk-3-dev`

## Initial Setup

### 1. Clone the Repository
```bash
# Clone the main repository
git clone https://github.com/your-org/social-download-manager.git
cd social-download-manager

# Set up remote for your fork (if contributing)
git remote add fork https://github.com/your-username/social-download-manager.git
```

### 2. Install Dependencies
```bash
# Install Node.js dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt

# Install development dependencies
npm install --save-dev

# Install pre-commit hooks
npm run setup:hooks
```

### 3. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your configuration
# Add API keys for development/testing (optional)
```

**Example .env file**:
```env
# Development Configuration
NODE_ENV=development
LOG_LEVEL=debug
DEBUG_MODE=true

# API Keys for Testing (Optional)
OPENAI_API_KEY=your_openai_key_here
PERPLEXITY_API_KEY=your_perplexity_key_here

# Database Configuration
DB_PATH=./data/database/dev.db

# Server Configuration
PORT=3000
HOST=localhost
```

### 4. Initial Build
```bash
# Build the application
npm run build

# Verify installation
npm run verify

# Run development server
npm run dev
```

## Development Dependencies

### Core Dependencies
- **Electron**: Desktop application framework
- **React**: UI framework
- **TypeScript**: Type-safe JavaScript
- **Webpack**: Module bundler
- **SQLite**: Database for development

### Development Tools
- **ESLint**: Code linting
- **Prettier**: Code formatting
- **Jest**: Testing framework
- **Electron Builder**: Application packaging
- **Husky**: Git hooks

### Testing Dependencies
- **@testing-library/react**: React component testing
- **@testing-library/jest-dom**: Jest DOM matchers
- **puppeteer**: End-to-end testing
- **supertest**: API testing

## Build System

### Available Scripts

```bash
# Development
npm run dev           # Start development server with hot reload
npm run dev:debug     # Start with debugging enabled
npm run dev:verbose   # Start with verbose logging

# Building
npm run build         # Production build
npm run build:dev     # Development build with source maps
npm run build:analyze # Build with bundle analysis

# Testing
npm test              # Run all tests
npm run test:watch    # Run tests in watch mode
npm run test:coverage # Run tests with coverage report
npm run test:e2e      # Run end-to-end tests

# Linting and Formatting
npm run lint          # Run ESLint
npm run lint:fix      # Fix auto-fixable ESLint errors
npm run format        # Format code with Prettier
npm run format:check  # Check if code is formatted

# Database
npm run db:create     # Create development database
npm run db:migrate    # Run database migrations
npm run db:seed       # Seed database with test data
npm run db:reset      # Reset database to clean state

# Packaging
npm run package       # Package for current platform
npm run package:all   # Package for all platforms
npm run dist          # Create distribution packages
```

### Build Configuration

The build system uses Webpack with different configurations:

**webpack.dev.js**: Development configuration
- Hot module replacement
- Source maps
- Debug symbols
- Fast builds

**webpack.prod.js**: Production configuration
- Code minification
- Bundle optimization
- Tree shaking
- Performance budgets

**webpack.common.js**: Shared configuration
- Entry points
- Module resolution
- Plugin setup

### Custom Build Options

```bash
# Build with specific target
npm run build -- --target=win32
npm run build -- --target=darwin
npm run build -- --target=linux

# Build with custom configuration
npm run build -- --config=custom-webpack.config.js

# Debug build process
DEBUG=webpack npm run build
```

## Development Workflow

### 1. Starting Development

```bash
# Start development environment
npm run dev

# In separate terminals:
npm run test:watch    # Continuous testing
npm run lint:watch    # Continuous linting
```

### 2. Making Changes

1. **Create feature branch**: `git checkout -b feature/your-feature-name`
2. **Make changes**: Edit code following style guidelines
3. **Test changes**: Ensure all tests pass
4. **Commit changes**: Use conventional commit messages

### 3. Code Style Guidelines

**TypeScript/JavaScript**:
```typescript
// Use TypeScript for all new code
interface DownloadConfig {
  quality: 'HD' | 'SD' | 'Mobile';
  format: 'mp4' | 'mp3';
  removeWatermark: boolean;
}

// Use descriptive names
const processVideoDownload = async (config: DownloadConfig): Promise<DownloadResult> => {
  // Implementation
};

// Use async/await over promises
const result = await processVideoDownload(config);
```

**File Structure**:
```
src/
├── components/        # React components
├── services/         # Business logic
├── utils/           # Utility functions
├── types/           # TypeScript definitions
├── hooks/           # React hooks
└── styles/          # CSS/SCSS files
```

### 4. Testing Requirements

All changes must include appropriate tests:

```typescript
// Component tests
import { render, screen } from '@testing-library/react';
import { DownloadButton } from './DownloadButton';

describe('DownloadButton', () => {
  it('should render correctly', () => {
    render(<DownloadButton />);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });
});

// Service tests
import { DownloadService } from './DownloadService';

describe('DownloadService', () => {
  it('should process TikTok URLs correctly', async () => {
    const service = new DownloadService();
    const result = await service.processUrl('https://tiktok.com/test');
    expect(result.platform).toBe('tiktok');
  });
});
```

## Debugging and Testing

### Development Server Debugging

```bash
# Start with debugging enabled
npm run dev:debug

# Enable specific debug modules
DEBUG=app:* npm run dev
DEBUG=download:*,platform:* npm run dev
```

### VS Code Debugging Configuration

**.vscode/launch.json**:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug Main Process",
      "type": "node",
      "request": "launch",
      "program": "${workspaceFolder}/src/main.ts",
      "outFiles": ["${workspaceFolder}/dist/**/*.js"],
      "env": {
        "NODE_ENV": "development",
        "DEBUG": "app:*"
      }
    },
    {
      "name": "Debug Renderer Process",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:3000",
      "webRoot": "${workspaceFolder}/src"
    }
  ]
}
```

### Testing Setup

```bash
# Run specific test files
npm test -- --testPathPattern=DownloadService

# Run tests with debugging
npm test -- --runInBand --detectOpenHandles

# Generate coverage report
npm run test:coverage
open coverage/lcov-report/index.html
```

### Database Testing

```bash
# Create test database
npm run db:create:test

# Run database tests
npm run test:db

# Reset test database
npm run db:reset:test
```

## Git Workflow

### Branch Strategy

- **main**: Production-ready code
- **develop**: Integration branch for features
- **feature/***: Feature development branches
- **hotfix/***: Critical fixes for production
- **release/***: Release preparation branches

### Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Feature commits
git commit -m "feat(download): add TikTok watermark removal"
git commit -m "feat(ui): implement dark theme support"

# Bug fixes
git commit -m "fix(platform): resolve YouTube URL parsing issue"
git commit -m "fix(db): handle migration error gracefully"

# Documentation
git commit -m "docs(api): update REST API documentation"

# Performance improvements
git commit -m "perf(download): optimize concurrent download handling"

# Refactoring
git commit -m "refactor(service): simplify error handling logic"
```

### Pre-commit Hooks

Husky runs these checks before each commit:

1. **Lint**: ESLint checks
2. **Format**: Prettier formatting
3. **Test**: Run affected tests
4. **Type check**: TypeScript compilation
5. **Audit**: Security vulnerability check

### Pull Request Process

1. **Create PR**: Against develop branch
2. **Fill template**: Use provided PR template
3. **Request review**: Assign reviewers
4. **Address feedback**: Make requested changes
5. **Merge**: After approval and CI passes

## IDE Configuration

### VS Code Extensions

Required extensions:
- ESLint
- Prettier
- TypeScript and JavaScript Language Features
- GitLens
- Thunder Client (for API testing)

Recommended extensions:
- Auto Rename Tag
- Bracket Pair Colorizer
- Material Icon Theme
- Path Intellisense

### VS Code Settings

**.vscode/settings.json**:
```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "typescript.preferences.importModuleSpecifier": "relative",
  "files.exclude": {
    "**/node_modules": true,
    "**/dist": true,
    "**/.git": true
  }
}
```

### WebStorm Configuration

1. **Enable ESLint**: File → Settings → Languages & Frameworks → JavaScript → Code Quality Tools → ESLint
2. **Enable Prettier**: File → Settings → Languages & Frameworks → JavaScript → Prettier
3. **Configure TypeScript**: File → Settings → Languages & Frameworks → TypeScript

## Troubleshooting

### Common Issues

**Node modules issues**:
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

**Python dependency issues**:
```bash
# Recreate virtual environment
rm -rf venv
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

**Build failures**:
```bash
# Clear build cache
npm run clean
npm run build

# Debug build process
DEBUG=webpack npm run build
```

**Database issues**:
```bash
# Reset development database
npm run db:reset
npm run db:migrate
npm run db:seed
```

### Getting Help

1. **Check documentation**: Read existing docs thoroughly
2. **Search issues**: Look for similar problems in GitHub issues
3. **Ask in discussions**: Use GitHub Discussions for questions
4. **Contact maintainers**: Reach out to core team members

---

*Developer Setup Guide for Social Download Manager v2.0*
*Last updated: June 2025* 