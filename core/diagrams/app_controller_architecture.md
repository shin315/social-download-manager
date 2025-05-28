# App Controller Architecture Diagrams

## 1. Clean Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    🌐 External Layer                        │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │     UI      │  │  Database   │  │   External APIs     │  │
│  │ Components  │  │   Layer     │  │  (Platform APIs)    │  │
│  │             │  │             │  │   TikTok, YouTube   │  │
│  │ • MainWindow│  │ • SQLite    │  │   Instagram, etc.   │  │
│  │ • ProgressUI│  │ • Migration │  │                     │  │
│  │ • SettingsUI│  │ • Models    │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│         │                 │                       │         │
└─────────────────────────────────────────────────────────────┘
          │                 │                       │
┌─────────────────────────────────────────────────────────────┐
│                🎯 Interface Adapters Layer                  │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              🎯 APP CONTROLLER                          │ │
│  │                                                         │ │
│  │  Core Responsibilities:                                 │ │
│  │  • Component Lifecycle Management                      │ │
│  │  • Event Coordination & Communication                  │ │
│  │  • Service Layer Integration                           │ │
│  │  • Error Handling & Recovery                           │ │
│  │  • Configuration Management                            │ │
│  │  • Thread-Safe Operations                              │ │
│  │                                                         │ │
│  │  Components Registry:                                  │ │
│  │  ├─ UI Components                                      │ │
│  │  ├─ Platform Adapters                                  │ │
│  │  ├─ Configuration Manager                              │ │
│  │  ├─ Event Bus                                          │ │
│  │  └─ Service Registry                                   │ │
│  └─────────────────────────────────────────────────────────┘ │
│                               │                             │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                   🏢 Application Core Layer                 │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Service   │  │   Domain    │  │    Use Cases        │  │
│  │   Layer     │  │   Models    │  │   (Business Logic)  │  │
│  │             │  │             │  │                     │  │
│  │ • Content   │  │ • Content   │  │ • Download Content  │  │
│  │ • Analytics │  │ • Platform  │  │ • Extract Metadata  │  │
│  │ • Download  │  │ • User      │  │ • Manage Analytics  │  │
│  │ • Platform  │  │ • Download  │  │ • Handle Errors     │  │
│  │             │  │             │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 2. App Controller Component Architecture

```
                    ┌──────────────────────────────────────┐
                    │           APP CONTROLLER             │
                    │                                      │
                    │  ┌────────────────────────────────┐  │
                    │  │        Core State              │  │
                    │  │  • ControllerState (enum)     │  │
                    │  │  • Components Registry        │  │
                    │  │  • Service Registry           │  │
                    │  │  • Configuration              │  │
                    │  │  • Thread Lock (RLock)        │  │
                    │  └────────────────────────────────┘  │
                    │                                      │
┌───────────────────┤                                      ├───────────────────┐
│                   │  ┌────────────────────────────────┐  │                   │
│   EVENT SYSTEM    │  │      Lifecycle Management     │  │   SERVICE LAYER   │
│                   │  │  • initialize()               │  │                   │
│  ┌──────────────┐ │  │  • shutdown()                 │  │ ┌──────────────┐  │
│  │  Event Bus   │ │  │  • get_status()               │  │ │ Content      │  │
│  │              │ │  │  • handle_error()             │  │ │ Service      │  │
│  │ • Publish    │ │  └────────────────────────────────┘  │ │              │  │
│  │ • Subscribe  │ │                                      │ │ • create     │  │
│  │ • Handler    │ │  ┌────────────────────────────────┐  │ │ • retrieve   │  │
│  │   Registry   │ │  │    Component Management       │  │ │ • update     │  │
│  └──────────────┘ │  │  • register_component()       │  │ └──────────────┘  │
│                   │  │  • unregister_component()     │  │                   │
│  ┌──────────────┐ │  │  • get_component()            │  │ ┌──────────────┐  │
│  │ Event        │ │  └────────────────────────────────┘  │ │ Analytics    │  │
│  │ Handlers     │ │                                      │ │ Service      │  │
│  │              │ │  ┌────────────────────────────────┐  │ │              │  │
│  │ • UI         │ │  │      Service Integration      │  │ │ • overview   │  │
│  │ • Analytics  │ │  │  • get_content_service()      │  │ │ • reports    │  │
│  │ • Download   │ │  │  • get_analytics_service()    │  │ │ • metrics    │  │
│  │ • Custom     │ │  │  • get_download_service()     │  │ └──────────────┘  │
│  └──────────────┘ │  └────────────────────────────────┘  │                   │
│                   │                                      │ ┌──────────────┐  │
└───────────────────┤                                      ├─│ Download     │  │
                    │  ┌────────────────────────────────┐  │ │ Service      │  │
                    │  │     High-Level Operations     │  │ │              │  │
                    │  │  • create_content_from_url()  │  │ │ • start      │  │
                    │  │  • start_download()           │  │ │ • monitor    │  │
                    │  │  • get_analytics_overview()   │  │ │ • pause      │  │
                    │  └────────────────────────────────┘  │ │ • resume     │  │
                    │                                      │ └──────────────┘  │
                    └──────────────────────────────────────┘                   │
                                                                               │
                                                          └───────────────────┘
```

## 3. Event Flow Architecture

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐
│     UI      │    │  APP CONTROLLER │    │   EVENT BUS     │    │  SERVICES   │
│ Component   │    │                 │    │                 │    │             │
└─────────────┘    └─────────────────┘    └─────────────────┘    └─────────────┘
       │                     │                       │                    │
       │ 1. User Action      │                       │                    │
       │────────────────────▶│                       │                    │
       │                     │                       │                    │
       │                     │ 2. Business Operation │                    │
       │                     │──────────────────────────────────────────▶│
       │                     │                       │                    │
       │                     │                       │ 3. Service Event   │
       │                     │◀──────────────────────────────────────────│
       │                     │                       │                    │
       │                     │ 4. Publish Event      │                    │
       │                     │──────────────────────▶│                    │
       │                     │                       │                    │
       │ 5. Event Handler    │                       │ 6. Broadcast       │
       │◀────────────────────────────────────────────│                    │
       │                     │                       │                    │
       │ 7. Update UI        │                       │                    │
       │                     │                       │                    │

Event Types:
• APP_STARTUP / APP_SHUTDOWN
• DOWNLOAD_STARTED / DOWNLOAD_COMPLETED / DOWNLOAD_FAILED
• CONTENT_CREATED / CONTENT_UPDATED / CONTENT_DELETED
• ERROR_OCCURRED
• CONFIG_CHANGED
• CUSTOM_EVENT
```

## 4. Thread Safety Architecture

```
                    ┌────────────────────────────────────────┐
                    │          APP CONTROLLER                │
                    │                                        │
                    │  ┌──────────────────────────────────┐  │
                    │  │         Thread Safety            │  │
                    │  │                                  │  │
                    │  │     threading.RLock              │  │
                    │  │  ┌──────────────────────────────┐ │  │
┌─────────────┐     │  │  │    Protected Operations     │ │  │     ┌─────────────┐
│   Thread 1  │────────│  │  • Component Registration   │ │  │────▶│   Thread 2  │
│             │     │  │  │  • Service Access           │ │  │     │             │
│ • UI Update │     │  │  │  • State Transitions        │ │  │     │ • Background│
│ • User      │     │  │  │  • Error Handling           │ │  │     │   Processing│
│   Actions   │     │  │  │  • Configuration Access     │ │  │     │             │
└─────────────┘     │  │  └──────────────────────────────┘ │  │     └─────────────┘
                    │  └──────────────────────────────────┘  │
                    │                                        │
┌─────────────┐     │  ┌──────────────────────────────────┐  │     ┌─────────────┐
│   Thread 3  │────────│         Event Publishing         │  │────▶│   Thread 4  │
│             │     │  │                                  │  │     │             │
│ • Download  │     │  │  • Thread-safe event queuing    │  │     │ • Analytics │
│   Monitor   │     │  │  • Asynchronous event delivery  │  │     │   Collection│
│             │     │  │  • Handler registry protection  │  │     │             │
└─────────────┘     │  └──────────────────────────────────┘  │     └─────────────┘
                    │                                        │
                    └────────────────────────────────────────┘

Thread Safety Guarantees:
✅ Component registration/access
✅ Service method calls
✅ Event publishing/handling
✅ State transitions
✅ Configuration access
✅ Error handling
```

## 5. Error Handling Flow

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐
│  Any Layer  │    │  APP CONTROLLER │    │  Error Handlers │    │   Recovery  │
│             │    │                 │    │                 │    │   Actions   │
└─────────────┘    └─────────────────┘    └─────────────────┘    └─────────────┘
       │                     │                       │                    │
       │ 1. Exception        │                       │                    │
       │────────────────────▶│                       │                    │
       │                     │                       │                    │
       │                     │ 2. handle_error()     │                    │
       │                     │                       │                    │
       │                     │ 3. Log Error          │                    │
       │                     │────────────────────────────────────────────▶
       │                     │                       │                    │
       │                     │ 4. Publish Event      │                    │
       │                     │──────────────────────▶│                    │
       │                     │                       │                    │
       │                     │ 5. Call Handlers      │                    │
       │                     │──────────────────────▶│                    │
       │                     │                       │                    │
       │                     │                       │ 6. UI Notification │
       │                     │                       │───────────────────▶│
       │                     │                       │                    │
       │                     │                       │ 7. Metrics Update  │
       │                     │                       │───────────────────▶│
       │                     │                       │                    │
       │                     │                       │ 8. Recovery Action │
       │                     │                       │───────────────────▶│

Error Context Flow:
• Exception occurs in any layer
• Controller centralizes error handling
• Multiple handlers process the error
• Recovery actions are triggered
• System continues operation
```

## 6. Service Integration Pattern

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           APP CONTROLLER                                    │
│                                                                             │
│  ┌───────────────────────┐         ┌─────────────────────────────────────┐  │
│  │   Service Accessors   │         │         Service Registry           │  │
│  │                       │         │                                     │  │
│  │ get_content_service() │◀────────┤ • Service Discovery                │  │
│  │                       │         │ • Dependency Injection             │  │
│  │get_analytics_service()│◀────────┤ • Lifecycle Management             │  │
│  │                       │         │ • Interface Validation             │  │
│  │get_download_service() │◀────────┤                                     │  │
│  │                       │         │                                     │  │
│  └───────────────────────┘         └─────────────────────────────────────┘  │
│               │                                      │                      │
└─────────────────────────────────────────────────────────────────────────────┘
                │                                      │
                ▼                                      ▼
  ┌─────────────────────────┐              ┌─────────────────────────┐
  │     Service Layer       │              │    Implementation       │
  │                         │              │                         │
  │ ┌─────────────────────┐ │              │ ┌─────────────────────┐ │
  │ │  IContentService    │ │◀─────────────┤ │  ContentServiceImpl │ │
  │ │                     │ │              │ │                     │ │
  │ │ • create_content()  │ │              │ │ • Database access   │ │
  │ │ • get_content()     │ │              │ │ • Validation logic  │ │
  │ │ • update_content()  │ │              │ │ • Business rules    │ │
  │ └─────────────────────┘ │              │ └─────────────────────┘ │
  │                         │              │                         │
  │ ┌─────────────────────┐ │              │ ┌─────────────────────┐ │
  │ │ IAnalyticsService   │ │◀─────────────┤ │AnalyticsServiceImpl │ │
  │ │                     │ │              │ │                     │ │
  │ │ • get_overview()    │ │              │ │ • Metrics collection│ │
  │ │ • generate_report() │ │              │ │ • Data aggregation  │ │
  │ └─────────────────────┘ │              │ └─────────────────────┘ │
  │                         │              │                         │
  │ ┌─────────────────────┐ │              │ ┌─────────────────────┐ │
  │ │  IDownloadService   │ │◀─────────────┤ │ DownloadServiceImpl │ │
  │ │                     │ │              │ │                     │ │
  │ │ • start_download()  │ │              │ │ • Platform handling │ │
  │ │ • monitor_progress()│ │              │ │ • File management   │ │
  │ │ • cancel_download() │ │              │ │ • Progress tracking │ │
  │ └─────────────────────┘ │              │ └─────────────────────┘ │
  └─────────────────────────┘              └─────────────────────────┘
```

## 7. Component Lifecycle Management

```
                    ┌────────────────────────────────────────┐
                    │          INITIALIZATION PHASE          │
                    └────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────┐    ┌─────────────────────────────────────────────────────┐
│   Core Systems  │    │              APP CONTROLLER                         │
│                 │    │                                                     │
│ 1. Config Mgr   │───▶│  Initialize Order:                                  │
│ 2. Event Bus    │    │  ├─ 1. Configuration Manager                       │
│ 3. Database     │    │  ├─ 2. Event Bus                                   │
│ 4. Services     │    │  ├─ 3. Database Connection                         │
│                 │    │  ├─ 4. Service Registry                            │
└─────────────────┘    │  ├─ 5. Core Services                               │
                       │  └─ 6. Component Registration                      │
                       └─────────────────────────────────────────────────────┘
                                       │
                                       ▼
                    ┌────────────────────────────────────────┐
                    │            READY STATE                 │
                    │                                        │
                    │  • All components initialized          │
                    │  • Services available                  │
                    │  • Event system active                │
                    │  • Ready for operations                │
                    └────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────┐    ┌─────────────────────────────────────────────────────┐
│   Operations    │    │            RUNNING STATE                            │
│                 │    │                                                     │
│ • UI Events     │───▶│  Active Operations:                                 │
│ • Downloads     │    │  ├─ Component Management                            │
│ • Analytics     │    │  ├─ Event Processing                                │
│ • Config        │    │  ├─ Service Coordination                            │
│                 │    │  ├─ Error Handling                                  │
└─────────────────┘    │  └─ Background Tasks                                │
                       └─────────────────────────────────────────────────────┘
                                       │
                                       ▼
                    ┌────────────────────────────────────────┐
                    │          SHUTDOWN PHASE                │
                    │                                        │
                    │  Shutdown Order (Reverse):             │
                    │  ├─ 1. Remove Event Handlers           │
                    │  ├─ 2. Dispose Services                │
                    │  ├─ 3. Cleanup Components              │
                    │  ├─ 4. Close Database                  │
                    │  └─ 5. Final State: SHUTDOWN           │
                    └────────────────────────────────────────┘
```

These diagrams illustrate the comprehensive architecture of the App Controller, showing how it coordinates between different layers of the application while maintaining clean architecture principles, thread safety, and robust error handling. 