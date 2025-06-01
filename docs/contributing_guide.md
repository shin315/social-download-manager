# Social Download Manager v2.0 - Contributing Guide

## Welcome Contributors! 🎉

Thank you for your interest in contributing to Social Download Manager v2.0! This guide will help you get started with contributing code, documentation, bug reports, and feature requests.

## Table of Contents
- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Community Guidelines](#community-guidelines)
- [Recognition and Rewards](#recognition-and-rewards)

## Getting Started

### Prerequisites

Before contributing, make sure you have:

1. **Development Environment**: Follow the [Developer Setup Guide](developer_setup_guide.md)
2. **GitHub Account**: Required for submitting contributions
3. **Basic Knowledge**: 
   - TypeScript/JavaScript
   - React (for UI contributions)
   - Node.js and npm
   - Git version control

### First Steps

1. **Fork the Repository**:
   ```bash
   # Fork on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/social-download-manager.git
   cd social-download-manager
   
   # Add upstream remote
   git remote add upstream https://github.com/original-repo/social-download-manager.git
   ```

2. **Set Up Development Environment**:
   ```bash
   # Install dependencies
   npm install
   
   # Copy environment template
   cp .env.example .env
   
   # Run tests to verify setup
   npm test
   
   # Start development server
   npm run dev
   ```

3. **Choose Your First Contribution**:
   - Browse [good first issues](https://github.com/repo/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
   - Check [help wanted](https://github.com/repo/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) issues
   - Review the [project roadmap](https://github.com/repo/projects)

## Development Process

### Branch Strategy

We use **Git Flow** with these main branches:

- **`main`**: Production-ready code
- **`develop`**: Integration branch for new features
- **`feature/*`**: Feature development branches
- **`hotfix/*`**: Critical bug fixes
- **`release/*`**: Release preparation

### Workflow Steps

1. **Create Feature Branch**:
   ```bash
   # Update your fork
   git fetch upstream
   git checkout develop
   git merge upstream/develop
   
   # Create feature branch
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**:
   - Write code following our standards
   - Add tests for new functionality
   - Update documentation as needed

3. **Test Your Changes**:
   ```bash
   # Run all tests
   npm test
   
   # Run specific test suites
   npm run test:unit
   npm run test:integration
   npm run test:e2e
   
   # Check code quality
   npm run lint
   npm run format
   ```

4. **Commit Changes**:
   ```bash
   # Stage changes
   git add .
   
   # Commit with conventional format
   git commit -m "feat(platform): add TikTok playlist support"
   ```

5. **Submit Pull Request**:
   ```bash
   # Push to your fork
   git push origin feature/your-feature-name
   
   # Create PR on GitHub
   ```

### Conventional Commits

We use [Conventional Commits](https://www.conventionalcommits.org/) for clear commit history:

**Format**: `type(scope): description`

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting (no functional changes)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Scopes**:
- `platform`: Platform-specific changes
- `ui`: User interface changes
- `core`: Core application logic
- `db`: Database changes
- `api`: API changes
- `deps`: Dependency updates

**Examples**:
```bash
feat(platform): add Instagram story download support
fix(ui): resolve dark theme button visibility issue
docs(api): update REST API documentation
test(platform): add TikTok URL validation tests
```

## Code Standards

### TypeScript Guidelines

**Interfaces and Types**:
```typescript
// Use PascalCase for interfaces
interface DownloadConfig {
  quality: VideoQuality;
  format: VideoFormat;
  removeWatermark: boolean;
}

// Use specific types instead of 'any'
type VideoQuality = 'HD' | 'SD' | 'Mobile';
type PlatformType = 'tiktok' | 'youtube' | 'instagram';

// Document complex types
/**
 * Configuration for video download operations
 */
interface DownloadOptions {
  /** Video quality preference */
  quality: VideoQuality;
  /** Output format for the video */
  format: VideoFormat;
  /** Whether to remove platform watermarks */
  removeWatermark: boolean;
  /** Custom output filename (optional) */
  filename?: string;
}
```

**Function Standards**:
```typescript
// Use async/await instead of promises
async function downloadVideo(url: string, options: DownloadOptions): Promise<DownloadResult> {
  try {
    const platform = await detectPlatform(url);
    const metadata = await platform.analyze(url);
    return await platform.download(url, options);
  } catch (error) {
    logger.error('Download failed', { url, error });
    throw new DownloadError('Failed to download video', error);
  }
}

// Use descriptive parameter names
function validateVideoUrl(
  url: string,
  supportedPlatforms: PlatformType[]
): ValidationResult {
  // Implementation
}

// Prefer early returns
function processVideoMetadata(metadata: VideoMetadata): ProcessedMetadata {
  if (!metadata.title) {
    return { error: 'Missing title' };
  }
  
  if (!metadata.duration) {
    return { error: 'Missing duration' };
  }
  
  // Process valid metadata
  return {
    title: sanitizeTitle(metadata.title),
    duration: formatDuration(metadata.duration),
    thumbnail: optimizeThumbnail(metadata.thumbnail)
  };
}
```

**Error Handling**:
```typescript
// Create specific error classes
class PlatformError extends Error {
  constructor(
    message: string,
    public platform: string,
    public originalError?: Error
  ) {
    super(message);
    this.name = 'PlatformError';
  }
}

// Use error boundaries in React components
class ErrorBoundary extends React.Component<Props, State> {
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    logger.error('Component error', { error, errorInfo });
  }
  
  render() {
    if (this.state.hasError) {
      return <ErrorFallback onRetry={this.handleRetry} />;
    }
    return this.props.children;
  }
}
```

### React Component Guidelines

**Component Structure**:
```typescript
// Use functional components with hooks
interface DownloadButtonProps {
  url: string;
  onDownloadStart: (id: string) => void;
  onDownloadComplete: (result: DownloadResult) => void;
  disabled?: boolean;
}

export const DownloadButton: React.FC<DownloadButtonProps> = ({
  url,
  onDownloadStart,
  onDownloadComplete,
  disabled = false
}) => {
  const [isDownloading, setIsDownloading] = useState(false);
  const [progress, setProgress] = useState(0);
  
  const handleDownload = useCallback(async () => {
    if (!url || disabled) return;
    
    setIsDownloading(true);
    try {
      const downloadId = await startDownload(url);
      onDownloadStart(downloadId);
      
      const result = await waitForDownload(downloadId, setProgress);
      onDownloadComplete(result);
    } catch (error) {
      showErrorNotification('Download failed', error.message);
    } finally {
      setIsDownloading(false);
      setProgress(0);
    }
  }, [url, disabled, onDownloadStart, onDownloadComplete]);
  
  return (
    <Button
      onClick={handleDownload}
      disabled={disabled || isDownloading}
      className="download-button"
    >
      {isDownloading ? (
        <ProgressIndicator progress={progress} />
      ) : (
        'Download'
      )}
    </Button>
  );
};
```

**Styling Guidelines**:
```typescript
// Use CSS modules or styled-components
import styles from './DownloadButton.module.css';

// Or with styled-components
const StyledButton = styled.button<{ isLoading: boolean }>`
  background-color: ${props => props.isLoading ? '#ccc' : '#007bff'};
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: ${props => props.isLoading ? 'not-allowed' : 'pointer'};
  
  &:hover:not(:disabled) {
    background-color: #0056b3;
  }
`;
```

### File Organization

```
src/
├── components/
│   ├── common/          # Reusable components
│   │   ├── Button/
│   │   │   ├── Button.tsx
│   │   │   ├── Button.test.tsx
│   │   │   ├── Button.module.css
│   │   │   └── index.ts
│   │   └── Modal/
│   ├── feature/         # Feature-specific components
│   │   ├── DownloadManager/
│   │   └── PlatformSelector/
│   └── layout/          # Layout components
├── hooks/               # Custom React hooks
├── services/            # Business logic
├── types/               # TypeScript type definitions
├── utils/               # Utility functions
├── constants/           # Application constants
└── __tests__/           # Test utilities
```

## Testing Requirements

### Test Coverage Standards

- **Minimum Coverage**: 80% overall
- **Critical Paths**: 95% coverage
- **New Features**: 90% coverage required

### Testing Pyramid

1. **Unit Tests** (70%): Individual functions and components
2. **Integration Tests** (20%): Component interactions
3. **End-to-End Tests** (10%): Complete user workflows

### Unit Testing

```typescript
// Component testing with React Testing Library
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DownloadButton } from './DownloadButton';

describe('DownloadButton', () => {
  const mockProps = {
    url: 'https://tiktok.com/video/123',
    onDownloadStart: jest.fn(),
    onDownloadComplete: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render correctly', () => {
    render(<DownloadButton {...mockProps} />);
    expect(screen.getByRole('button', { name: /download/i })).toBeInTheDocument();
  });

  it('should start download when clicked', async () => {
    render(<DownloadButton {...mockProps} />);
    
    fireEvent.click(screen.getByRole('button', { name: /download/i }));
    
    await waitFor(() => {
      expect(mockProps.onDownloadStart).toHaveBeenCalledWith(expect.any(String));
    });
  });

  it('should show progress indicator while downloading', async () => {
    render(<DownloadButton {...mockProps} />);
    
    fireEvent.click(screen.getByRole('button'));
    
    await waitFor(() => {
      expect(screen.getByTestId('progress-indicator')).toBeInTheDocument();
    });
  });
});

// Service testing
import { DownloadService } from './DownloadService';
import { createMockPlatformRegistry } from '../__tests__/mocks';

describe('DownloadService', () => {
  let service: DownloadService;
  let mockPlatformRegistry: any;

  beforeEach(() => {
    mockPlatformRegistry = createMockPlatformRegistry();
    service = new DownloadService(mockPlatformRegistry);
  });

  it('should validate URL before download', async () => {
    const invalidUrl = 'not-a-url';
    
    await expect(service.startDownload(invalidUrl, {})).rejects.toThrow('Invalid URL');
  });

  it('should throw error for unsupported platform', async () => {
    const unsupportedUrl = 'https://unsupported.com/video/123';
    
    await expect(service.startDownload(unsupportedUrl, {})).rejects.toThrow('Unsupported platform');
  });
});
```

### Integration Testing

```typescript
// Testing component integration
import { render, screen } from '@testing-library/react';
import { DownloadManager } from './DownloadManager';
import { createMockDownloadService } from '../__tests__/mocks';

describe('DownloadManager Integration', () => {
  it('should handle complete download workflow', async () => {
    const mockService = createMockDownloadService();
    
    render(<DownloadManager downloadService={mockService} />);
    
    // Enter URL
    fireEvent.change(screen.getByLabelText(/url/i), {
      target: { value: 'https://tiktok.com/video/123' }
    });
    
    // Select quality
    fireEvent.change(screen.getByLabelText(/quality/i), {
      target: { value: 'HD' }
    });
    
    // Start download
    fireEvent.click(screen.getByRole('button', { name: /download/i }));
    
    // Verify download appears in queue
    await waitFor(() => {
      expect(screen.getByTestId('download-queue')).toContainElement(
        screen.getByText(/tiktok\.com/)
      );
    });
  });
});
```

### End-to-End Testing

```typescript
// E2E testing with Playwright
import { test, expect } from '@playwright/test';

test.describe('Download Workflow', () => {
  test('should download TikTok video successfully', async ({ page }) => {
    await page.goto('/');
    
    // Enter TikTok URL
    await page.fill('[data-testid="url-input"]', 'https://tiktok.com/video/123');
    
    // Select HD quality
    await page.selectOption('[data-testid="quality-select"]', 'HD');
    
    // Start download
    await page.click('[data-testid="download-button"]');
    
    // Wait for download to complete
    await expect(page.locator('[data-testid="download-status"]')).toContainText('Completed');
    
    // Verify file exists
    const downloadPath = await page.locator('[data-testid="file-path"]').textContent();
    // Additional file existence verification
  });

  test('should handle network errors gracefully', async ({ page }) => {
    // Mock network failure
    await page.route('**/api/download', route => route.abort());
    
    await page.goto('/');
    await page.fill('[data-testid="url-input"]', 'https://tiktok.com/video/123');
    await page.click('[data-testid="download-button"]');
    
    // Verify error handling
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();
  });
});
```

## Pull Request Process

### Before Submitting

1. **Self-Review**:
   - Read through your changes
   - Test thoroughly on different platforms
   - Update documentation
   - Add/update tests

2. **Code Quality Checks**:
   ```bash
   # Run linting
   npm run lint:fix
   
   # Format code
   npm run format
   
   # Type checking
   npm run type-check
   
   # Test coverage
   npm run test:coverage
   ```

### PR Template

When creating a PR, use this template:

```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Changes Made
- Detailed list of changes
- Files modified
- New dependencies added

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] E2E tests pass
- [ ] Manual testing completed

## Screenshots/Videos
(If applicable, add screenshots or videos demonstrating the change)

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Code is well-commented
- [ ] Tests added for new functionality
- [ ] Documentation updated
- [ ] No console errors or warnings
```

### Review Process

1. **Automated Checks**: All CI checks must pass
2. **Code Review**: At least one maintainer review required
3. **Testing**: Changes must be tested on multiple platforms
4. **Documentation**: Updates must include relevant documentation

### Review Criteria

Reviewers will check for:

- **Functionality**: Does it work as intended?
- **Code Quality**: Is it well-written and maintainable?
- **Performance**: Does it impact app performance?
- **Security**: Are there any security implications?
- **Compatibility**: Works across supported platforms?
- **Testing**: Adequate test coverage?
- **Documentation**: Clear and complete?

## Issue Reporting

### Bug Reports

Use the bug report template:

```markdown
## Bug Description
Clear description of the bug.

## Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. Scroll down to '...'
4. See error

## Expected Behavior
What you expected to happen.

## Actual Behavior
What actually happened.

## Environment
- OS: [e.g., Windows 10, macOS 12.1]
- App Version: [e.g., 2.0.1]
- Node.js Version: [e.g., 18.12.0]

## Screenshots/Logs
Add screenshots or error logs if applicable.

## Additional Context
Any other context about the problem.
```

### Feature Requests

Use the feature request template:

```markdown
## Feature Request
Clear description of the requested feature.

## Problem Statement
What problem does this feature solve?

## Proposed Solution
Detailed description of your proposed solution.

## Alternative Solutions
Other approaches you've considered.

## Additional Context
Mockups, examples, or related issues.
```

### Issue Labels

We use these labels for organization:

- **Type**: `bug`, `feature`, `enhancement`, `documentation`
- **Priority**: `low`, `medium`, `high`, `critical`
- **Difficulty**: `good first issue`, `help wanted`, `expert needed`
- **Status**: `needs triage`, `in progress`, `blocked`, `ready for review`
- **Platform**: `windows`, `macos`, `linux`, `cross-platform`

## Community Guidelines

### Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please:

- **Be Respectful**: Treat everyone with respect and kindness
- **Be Collaborative**: Help others and ask for help when needed
- **Be Constructive**: Provide helpful feedback and suggestions
- **Be Patient**: Understand that people have different skill levels
- **Be Professional**: Maintain a professional tone in all interactions

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and community chat
- **Discord**: Real-time community chat (link in README)
- **Email**: Direct contact for sensitive issues

### Getting Help

If you need help:

1. **Check Documentation**: Start with existing docs
2. **Search Issues**: Look for similar questions
3. **Ask in Discussions**: Use GitHub Discussions for questions
4. **Join Discord**: Real-time help from the community

### Mentorship Program

We offer mentorship for new contributors:

- **First-Time Contributors**: Guidance on making your first PR
- **Feature Development**: Help designing and implementing new features
- **Testing**: Learn our testing practices and tools
- **Documentation**: Improve your technical writing skills

To request a mentor, comment on a "good first issue" or reach out in Discord.

## Recognition and Rewards

### Contributor Recognition

We recognize contributions in several ways:

- **Contributors Page**: Listed on our website
- **Release Notes**: Mentioned in release announcements
- **Social Media**: Highlighted on our social channels
- **Contributor Badge**: Special Discord role

### Special Recognition

Outstanding contributors may receive:

- **Core Contributor Status**: Commit access and review privileges
- **Conference Speaking**: Opportunities to present about the project
- **Swag**: Project stickers, t-shirts, and other items
- **Early Access**: Try new features before public release

### Hall of Fame

Our top contributors are featured in our Hall of Fame:

- **Most Commits**: Highest number of accepted commits
- **Best Mentor**: Most helpful to new contributors
- **Innovation Award**: Most creative solutions
- **Community Champion**: Outstanding community support

## Conclusion

Thank you for contributing to Social Download Manager v2.0! Your efforts help make this project better for everyone. If you have questions or suggestions about this contributing guide, please open an issue or discussion.

**Remember**: Every contribution matters, whether it's code, documentation, bug reports, or helping other users. Welcome to the community! 🚀

---

*Contributing Guide for Social Download Manager v2.0*
*Last updated: June 2025*
*Happy Contributing! 🎉* 