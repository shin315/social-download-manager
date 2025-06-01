# Social Download Manager v2.0 - Extension Development Guide

## Building Extensions and Plugins

This guide covers creating extensions for Social Download Manager v2.0, including platform handlers, UI components, and service integrations.

## Table of Contents
- [Plugin System Overview](#plugin-system-overview)
- [Creating Platform Handlers](#creating-platform-handlers)
- [UI Extensions](#ui-extensions)
- [Service Integrations](#service-integrations)
- [Plugin Development Workflow](#plugin-development-workflow)
- [Testing Extensions](#testing-extensions)
- [Publishing and Distribution](#publishing-and-distribution)
- [Advanced Extension Patterns](#advanced-extension-patterns)

## Plugin System Overview

### Plugin Types

Social Download Manager v2.0 supports four main types of plugins:

1. **Platform Plugins**: Add support for new video platforms
2. **UI Plugins**: Extend the user interface with new components
3. **Integration Plugins**: Connect with external services
4. **Utility Plugins**: Add general-purpose functionality

### Plugin Structure

Every plugin follows this basic structure:

```
my-plugin/
├── package.json          # Plugin metadata
├── plugin.manifest.json  # Plugin configuration
├── src/
│   ├── index.ts          # Main plugin entry point
│   ├── handlers/         # Platform handlers (if applicable)
│   ├── components/       # UI components (if applicable)
│   └── services/         # Services and utilities
├── tests/                # Plugin tests
└── README.md            # Plugin documentation
```

### Basic Plugin Template

```typescript
// src/index.ts
import { Plugin, PluginContext } from '@social-download-manager/plugin-api';

export default class MyPlugin implements Plugin {
  id = 'my-plugin';
  name = 'My Awesome Plugin';
  version = '1.0.0';
  type = 'platform' as const;

  private context?: PluginContext;

  async initialize(context: PluginContext): Promise<void> {
    this.context = context;
    
    // Initialize your plugin here
    console.log('MyPlugin initialized');
  }

  async destroy(): Promise<void> {
    // Cleanup resources
    console.log('MyPlugin destroyed');
  }
}
```

**Plugin Manifest** (`plugin.manifest.json`):
```json
{
  "id": "my-plugin",
  "name": "My Awesome Plugin", 
  "version": "1.0.0",
  "description": "A sample plugin for Social Download Manager",
  "author": "Your Name",
  "type": "platform",
  "entry": "dist/index.js",
  "permissions": [
    "network",
    "filesystem"
  ],
  "dependencies": {
    "@social-download-manager/plugin-api": "^2.0.0"
  },
  "platforms": ["tiktok", "custom-platform"],
  "supportedVersions": "^2.0.0"
}
```

## Creating Platform Handlers

### Platform Plugin Interface

```typescript
import { PlatformPlugin, VideoMetadata, DownloadOptions, DownloadChunk } from '@social-download-manager/plugin-api';

export class MyPlatformPlugin implements PlatformPlugin {
  id = 'my-platform-plugin';
  name = 'My Platform Handler';
  version = '1.0.0';
  type = 'platform' as const;
  platform = 'myplatform' as const;

  private context?: PluginContext;

  async initialize(context: PluginContext): Promise<void> {
    this.context = context;
    
    // Register URL patterns this platform handles
    context.platformRegistry.register(this);
  }

  supports(url: string): boolean {
    // Define URL patterns your platform supports
    return /^https?:\/\/(www\.)?myplatform\.com\//.test(url);
  }

  async analyze(url: string): Promise<VideoMetadata> {
    // Extract video metadata from the URL
    const response = await this.context!.httpClient.get(url);
    
    return {
      title: this.extractTitle(response.data),
      description: this.extractDescription(response.data),
      thumbnail: this.extractThumbnail(response.data),
      duration: this.extractDuration(response.data),
      creator: this.extractCreator(response.data),
      availableQualities: this.extractQualities(response.data),
      tags: this.extractTags(response.data)
    };
  }

  async *download(url: string, options: DownloadOptions): AsyncIterable<DownloadChunk> {
    // Implement download logic
    const metadata = await this.analyze(url);
    const downloadUrl = await this.getDownloadUrl(url, options.quality);
    
    const response = await this.context!.httpClient.getStream(downloadUrl);
    
    let downloaded = 0;
    const totalSize = parseInt(response.headers['content-length'] || '0');

    for await (const chunk of response.data) {
      downloaded += chunk.length;
      
      yield {
        data: chunk,
        progress: totalSize > 0 ? downloaded / totalSize : 0,
        downloaded,
        totalSize
      };
    }
  }

  private extractTitle(html: string): string {
    // Implementation for extracting title from HTML
    const match = html.match(/<title>(.+?)<\/title>/);
    return match ? match[1] : 'Unknown Title';
  }

  private async getDownloadUrl(videoUrl: string, quality: string): Promise<string> {
    // Implementation for getting direct download URL
    // This might involve API calls, parsing, etc.
    throw new Error('Method not implemented');
  }

  async destroy(): Promise<void> {
    // Cleanup resources
  }
}
```

### Advanced Platform Features

**Quality Selection**:
```typescript
interface QualityInfo {
  label: string;
  value: string;
  resolution: string;
  fileSize?: number;
  codec?: string;
}

async getAvailableQualities(url: string): Promise<QualityInfo[]> {
  const metadata = await this.analyze(url);
  
  return [
    { label: '1080p HD', value: '1080p', resolution: '1920x1080', codec: 'h264' },
    { label: '720p HD', value: '720p', resolution: '1280x720', codec: 'h264' },
    { label: '480p', value: '480p', resolution: '854x480', codec: 'h264' }
  ];
}
```

**Authentication Handling**:
```typescript
class AuthenticatedPlatformPlugin extends MyPlatformPlugin {
  private accessToken?: string;

  async authenticate(credentials: any): Promise<void> {
    const response = await this.context!.httpClient.post('/api/auth', {
      username: credentials.username,
      password: credentials.password
    });
    
    this.accessToken = response.data.accessToken;
    
    // Store token securely
    await this.context!.storage.setSecure('myplatform_token', this.accessToken);
  }

  async download(url: string, options: DownloadOptions): AsyncIterable<DownloadChunk> {
    // Include authentication in requests
    if (!this.accessToken) {
      throw new Error('Authentication required');
    }

    // Add auth headers to requests
    this.context!.httpClient.defaults.headers.Authorization = `Bearer ${this.accessToken}`;
    
    yield* super.download(url, options);
  }
}
```

## UI Extensions

### Creating UI Components

```typescript
// src/components/MyCustomComponent.tsx
import React from 'react';
import { UIPlugin } from '@social-download-manager/plugin-api';

interface MyComponentProps {
  data: any;
  onAction: (action: string) => void;
}

export const MyCustomComponent: React.FC<MyComponentProps> = ({ data, onAction }) => {
  return (
    <div className="my-custom-component">
      <h3>Custom Feature</h3>
      <p>This is a custom UI component from a plugin</p>
      <button onClick={() => onAction('customAction')}>
        Perform Custom Action
      </button>
    </div>
  );
};

// Plugin implementation
export class MyUIPlugin implements UIPlugin {
  id = 'my-ui-plugin';
  name = 'My UI Plugin';
  version = '1.0.0';
  type = 'ui' as const;
  component = MyCustomComponent;
  location = 'sidebar' as const; // or 'toolbar', 'modal', 'tab'

  async initialize(context: PluginContext): Promise<void> {
    // Register the component
    context.componentRegistry?.register(this.location, this.component);
  }

  async destroy(): Promise<void> {
    // Unregister component if needed
  }
}
```

### UI Plugin Locations

Available locations for UI components:

- **`sidebar`**: Add panels to the sidebar
- **`toolbar`**: Add buttons to the toolbar
- **`tab`**: Add new tabs to the main interface
- **`modal`**: Register modal dialogs
- **`menu`**: Add items to context menus
- **`status`**: Add status indicators

### Theme Integration

```typescript
// Using the theme system in UI components
import { useTheme } from '@social-download-manager/ui-kit';

export const ThemedComponent: React.FC = () => {
  const theme = useTheme();
  
  return (
    <div style={{
      backgroundColor: theme.colors.background,
      color: theme.colors.text,
      border: `1px solid ${theme.colors.border}`
    }}>
      <h3 style={{ color: theme.colors.primary }}>Themed Component</h3>
    </div>
  );
};
```

## Service Integrations

### Integration Plugin Template

```typescript
import { IntegrationPlugin, PluginContext } from '@social-download-manager/plugin-api';

export class CloudStorageIntegration implements IntegrationPlugin {
  id = 'cloud-storage-integration';
  name = 'Cloud Storage Integration';
  version = '1.0.0';
  type = 'integration' as const;
  service = 'cloud-storage';

  private context?: PluginContext;
  private apiClient?: any;

  async initialize(context: PluginContext): Promise<void> {
    this.context = context;
    
    // Listen for download completion events
    context.eventBus.on('download:completed', this.handleDownloadCompleted.bind(this));
  }

  async connect(credentials: any): Promise<void> {
    // Initialize API client with credentials
    this.apiClient = new CloudStorageAPI({
      apiKey: credentials.apiKey,
      secretKey: credentials.secretKey
    });
    
    // Test connection
    await this.apiClient.testConnection();
  }

  async sync(data: any): Promise<void> {
    if (!this.apiClient) {
      throw new Error('Not connected to cloud storage');
    }

    // Upload file to cloud storage
    await this.apiClient.upload(data.filePath, {
      folder: '/SocialDownloadManager',
      metadata: {
        originalUrl: data.url,
        platform: data.platform,
        downloadDate: new Date().toISOString()
      }
    });
  }

  private async handleDownloadCompleted(event: any): Promise<void> {
    // Auto-sync completed downloads if enabled
    const autoSync = await this.context!.storage.get('cloudStorage.autoSync');
    
    if (autoSync) {
      try {
        await this.sync(event);
        this.context!.logger.info('File synced to cloud storage', { file: event.filePath });
      } catch (error) {
        this.context!.logger.error('Failed to sync file', { error, file: event.filePath });
      }
    }
  }

  async destroy(): Promise<void> {
    // Cleanup
    this.apiClient = null;
  }
}
```

### Configuration Management

```typescript
// Plugin configuration schema
interface PluginConfig {
  enabled: boolean;
  autoSync: boolean;
  syncFolder: string;
  compression: 'none' | 'zip' | 'gzip';
  retention: number; // days
}

class ConfigurablePlugin implements Plugin {
  private config: PluginConfig = {
    enabled: true,
    autoSync: false,
    syncFolder: '/SocialDownloadManager',
    compression: 'none',
    retention: 30
  };

  async initialize(context: PluginContext): Promise<void> {
    // Load configuration
    const savedConfig = await context.storage.get('myPlugin.config');
    if (savedConfig) {
      this.config = { ...this.config, ...savedConfig };
    }
    
    // Provide configuration UI
    this.registerConfigUI(context);
  }

  private registerConfigUI(context: PluginContext): void {
    const configComponent = () => (
      <div>
        <h3>Plugin Configuration</h3>
        <label>
          <input
            type="checkbox"
            checked={this.config.enabled}
            onChange={(e) => this.updateConfig({ enabled: e.target.checked })}
          />
          Enable Plugin
        </label>
        {/* More configuration options */}
      </div>
    );

    context.componentRegistry?.register('settings', configComponent);
  }

  private async updateConfig(updates: Partial<PluginConfig>): Promise<void> {
    this.config = { ...this.config, ...updates };
    await this.context!.storage.set('myPlugin.config', this.config);
  }
}
```

## Plugin Development Workflow

### Development Setup

1. **Create Plugin Directory**:
```bash
mkdir my-awesome-plugin
cd my-awesome-plugin
npm init -y
```

2. **Install Dependencies**:
```bash
npm install @social-download-manager/plugin-api
npm install -D typescript @types/node
```

3. **Setup TypeScript**:
```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "tests"]
}
```

4. **Build Script**:
```json
// package.json
{
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch",
    "test": "jest"
  }
}
```

### Development Mode

Load your plugin in development mode:

```typescript
// In your main application's development config
const devPlugins = [
  {
    path: '/path/to/my-awesome-plugin',
    watch: true // Auto-reload on changes
  }
];
```

### Hot Reloading

Enable hot reloading for faster development:

```typescript
// Plugin development helper
class PluginDevHelper {
  private watcher?: any;

  enableHotReload(pluginPath: string): void {
    this.watcher = chokidar.watch(path.join(pluginPath, 'dist'), {
      ignored: /node_modules/,
      persistent: true
    });

    this.watcher.on('change', async (filePath: string) => {
      console.log(`Plugin file changed: ${filePath}`);
      await this.reloadPlugin(pluginPath);
    });
  }

  private async reloadPlugin(pluginPath: string): Promise<void> {
    // Unload current plugin
    await this.pluginManager.unload(pluginPath);
    
    // Clear require cache
    delete require.cache[require.resolve(pluginPath)];
    
    // Reload plugin
    await this.pluginManager.load(pluginPath);
  }
}
```

## Testing Extensions

### Unit Testing

```typescript
// tests/MyPlatformPlugin.test.ts
import { MyPlatformPlugin } from '../src/MyPlatformPlugin';
import { createMockContext } from '@social-download-manager/plugin-testing';

describe('MyPlatformPlugin', () => {
  let plugin: MyPlatformPlugin;
  let mockContext: any;

  beforeEach(async () => {
    mockContext = createMockContext();
    plugin = new MyPlatformPlugin();
    await plugin.initialize(mockContext);
  });

  afterEach(async () => {
    await plugin.destroy();
  });

  it('should support platform URLs', () => {
    expect(plugin.supports('https://myplatform.com/video/123')).toBe(true);
    expect(plugin.supports('https://other.com/video/123')).toBe(false);
  });

  it('should analyze video metadata', async () => {
    // Mock HTTP response
    mockContext.httpClient.get.mockResolvedValue({
      data: '<title>Test Video</title>'
    });

    const metadata = await plugin.analyze('https://myplatform.com/video/123');
    
    expect(metadata.title).toBe('Test Video');
    expect(mockContext.httpClient.get).toHaveBeenCalledWith('https://myplatform.com/video/123');
  });

  it('should download video chunks', async () => {
    // Mock download stream
    const mockChunks = [
      Buffer.from('chunk1'),
      Buffer.from('chunk2')
    ];

    mockContext.httpClient.getStream.mockResolvedValue({
      data: mockChunks,
      headers: { 'content-length': '12' }
    });

    const chunks: any[] = [];
    for await (const chunk of plugin.download('https://myplatform.com/video/123', { quality: '720p' })) {
      chunks.push(chunk);
    }

    expect(chunks).toHaveLength(2);
    expect(chunks[0].progress).toBeGreaterThan(0);
  });
});
```

### Integration Testing

```typescript
// tests/integration.test.ts
import { PluginManager } from '@social-download-manager/core';
import { MyPlatformPlugin } from '../src/MyPlatformPlugin';

describe('Plugin Integration', () => {
  let pluginManager: PluginManager;

  beforeEach(async () => {
    pluginManager = new PluginManager();
    await pluginManager.initialize();
  });

  afterEach(async () => {
    await pluginManager.destroy();
  });

  it('should load and register plugin', async () => {
    await pluginManager.loadPlugin('./dist');
    
    const registeredPlatforms = pluginManager.getRegisteredPlatforms();
    expect(registeredPlatforms).toContain('myplatform');
  });

  it('should handle real download workflow', async () => {
    await pluginManager.loadPlugin('./dist');
    
    const downloadService = pluginManager.getService('download');
    const downloadId = await downloadService.startDownload(
      'https://myplatform.com/video/123',
      { quality: '720p' }
    );

    expect(downloadId).toBeDefined();
    
    // Wait for download completion or timeout
    await new Promise(resolve => setTimeout(resolve, 5000));
  });
});
```

### End-to-End Testing

```typescript
// tests/e2e.test.ts
import { Application } from 'spectron';
import { join } from 'path';

describe('Plugin E2E Tests', () => {
  let app: Application;

  beforeEach(async () => {
    app = new Application({
      path: join(__dirname, '../../../node_modules/.bin/electron'),
      args: [join(__dirname, '../../../dist/main.js')],
      env: { NODE_ENV: 'test' }
    });

    await app.start();
    
    // Install test plugin
    await app.client.execute(() => {
      // Plugin installation logic
    });
  });

  afterEach(async () => {
    if (app && app.isRunning()) {
      await app.stop();
    }
  });

  it('should show plugin in platform selector', async () => {
    const platforms = await app.client.$$('[data-testid="platform-selector"] option');
    const platformTexts = await Promise.all(
      platforms.map(platform => platform.getText())
    );
    
    expect(platformTexts).toContain('My Platform');
  });

  it('should download from custom platform', async () => {
    // Enter URL
    await app.client.setValue('[data-testid="url-input"]', 'https://myplatform.com/video/123');
    
    // Click download
    await app.client.click('[data-testid="download-button"]');
    
    // Wait for download to appear in queue
    await app.client.waitForExist('[data-testid="download-item"]', 5000);
    
    const downloadItem = await app.client.$('[data-testid="download-item"]');
    expect(await downloadItem.isDisplayed()).toBe(true);
  });
});
```

## Publishing and Distribution

### Plugin Registry

Submit your plugin to the official registry:

```bash
# Build and package
npm run build
npm pack

# Submit to registry
npm publish --registry=https://plugins.social-download-manager.com
```

### Manual Distribution

Distribute your plugin manually:

```bash
# Create distribution package
npm run build
tar -czf my-awesome-plugin-v1.0.0.tar.gz dist/ plugin.manifest.json package.json README.md

# Users can install with:
# SDM Plugin Manager -> Install from File -> my-awesome-plugin-v1.0.0.tar.gz
```

### Plugin Metadata

```json
// plugin.manifest.json - Full example
{
  "id": "my-awesome-plugin",
  "name": "My Awesome Plugin",
  "version": "1.0.0",
  "description": "Adds support for MyPlatform video downloads",
  "author": {
    "name": "Your Name",
    "email": "you@example.com",
    "url": "https://yourwebsite.com"
  },
  "license": "MIT",
  "homepage": "https://github.com/you/my-awesome-plugin",
  "repository": {
    "type": "git",
    "url": "https://github.com/you/my-awesome-plugin.git"
  },
  "bugs": {
    "url": "https://github.com/you/my-awesome-plugin/issues"
  },
  "type": "platform",
  "entry": "dist/index.js",
  "permissions": [
    "network",
    "filesystem",
    "notifications"
  ],
  "platforms": ["myplatform"],
  "supportedVersions": "^2.0.0",
  "dependencies": {
    "@social-download-manager/plugin-api": "^2.0.0"
  },
  "keywords": [
    "social-download-manager",
    "plugin",
    "video-downloader",
    "myplatform"
  ],
  "screenshots": [
    "screenshots/main.png",
    "screenshots/settings.png"
  ],
  "icon": "icon.png"
}
```

## Advanced Extension Patterns

### Plugin Communication

```typescript
// Cross-plugin communication via event bus
class AnalyticsPlugin implements Plugin {
  async initialize(context: PluginContext): Promise<void> {
    // Listen to events from other plugins
    context.eventBus.on('download:completed', this.trackDownload.bind(this));
    context.eventBus.on('plugin:custom-event', this.handleCustomEvent.bind(this));
  }

  private trackDownload(event: any): void {
    // Track download analytics
    this.sendAnalytics('download_completed', {
      platform: event.platform,
      quality: event.quality,
      duration: event.duration
    });
  }

  // Emit custom events for other plugins
  private emitCustomEvent(data: any): void {
    this.context!.eventBus.emit('analytics:data-available', {
      type: 'download_stats',
      data
    });
  }
}
```

### Middleware Pattern

```typescript
// Download middleware for processing
interface DownloadMiddleware {
  name: string;
  priority: number;
  process(context: DownloadContext): Promise<DownloadContext>;
}

class WatermarkRemovalMiddleware implements DownloadMiddleware {
  name = 'watermark-removal';
  priority = 100;

  async process(context: DownloadContext): Promise<DownloadContext> {
    if (context.options.removeWatermark && context.platform === 'tiktok') {
      // Process video to remove watermark
      const processedVideo = await this.removeWatermark(context.videoStream);
      return {
        ...context,
        videoStream: processedVideo
      };
    }
    return context;
  }

  private async removeWatermark(videoStream: any): Promise<any> {
    // Watermark removal implementation
  }
}
```

### State Management

```typescript
// Plugin state management
class StatefulPlugin implements Plugin {
  private state: PluginState = {};

  async initialize(context: PluginContext): Promise<void> {
    // Load persistent state
    this.state = await context.storage.get('myPlugin.state') || {};
    
    // Subscribe to state changes
    context.eventBus.on('app:shutdown', this.saveState.bind(this));
  }

  private async saveState(): Promise<void> {
    await this.context!.storage.set('myPlugin.state', this.state);
  }

  updateState(updates: Partial<PluginState>): void {
    this.state = { ...this.state, ...updates };
    
    // Emit state change event
    this.context!.eventBus.emit('plugin:state-changed', {
      plugin: this.id,
      state: this.state
    });
  }
}
```

---

*Extension Development Guide for Social Download Manager v2.0*
*Last updated: June 2025* 