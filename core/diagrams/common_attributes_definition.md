# Common Attributes Definition for Social Download Manager v2.0

## Overview

This document establishes standardized attributes, naming conventions, and design patterns that ensure consistency across all database tables in the Social Download Manager v2.0 schema.

## Core Design Principles

### 1. **Naming Conventions**

#### Table Names
- Use **singular form** with **snake_case**: `content`, `download`, `platform`
- Junction tables: `{table1}_{table2}` format: `content_tags`, `user_roles`
- Avoid abbreviations unless widely understood: `url` ✅, `usr` ❌

#### Column Names
- Use **snake_case** for all column names: `created_at`, `user_id`, `video_quality`
- Boolean fields: prefix with `is_`, `has_`, `can_`: `is_active`, `has_thumbnail`, `can_download`
- Foreign keys: `{referenced_table}_id`: `platform_id`, `content_id`
- Timestamps: descriptive suffixes: `created_at`, `updated_at`, `deleted_at`, `published_at`

#### Constraints and Indexes
- Constraints: `chk_{table}_{description}`: `chk_content_positive_metrics`
- Indexes: `idx_{table}_{columns}`: `idx_content_platform_status`
- Unique constraints: `uq_{table}_{columns}`: `uq_content_platform_content_id`

### 2. **Standard Data Types**

#### SQLite Type Mappings
```sql
-- Primary data types
INTEGER          -- IDs, counts, timestamps (epoch), boolean (0/1)
TEXT             -- Strings, URLs, JSON, descriptions
REAL             -- Floating point numbers, percentages
BLOB             -- Binary data (future: thumbnails, cached data)
NUMERIC          -- Decimal values (file sizes, exact monetary values)

-- Commonly used text lengths (as documentation)
VARCHAR(50)      -- Short identifiers, status values
VARCHAR(100)     -- Names, titles (short)
VARCHAR(255)     -- Standard text fields, file paths
TEXT             -- Long descriptions, JSON data, unlimited text
```

### 3. **Universal Attributes**

#### Primary Keys
Every table MUST have a primary key:
```sql
-- Standard auto-increment primary key
id INTEGER PRIMARY KEY AUTOINCREMENT

-- Compound primary keys for junction tables
PRIMARY KEY (table1_id, table2_id)

-- Natural keys where appropriate (rare)
name VARCHAR(50) PRIMARY KEY  -- For reference tables only
```

#### Timestamp Fields
Standard timestamp pattern for all main entities:
```sql
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

**Optional timestamp fields:**
```sql
deleted_at TIMESTAMP,           -- For soft deletes
published_at TIMESTAMP,         -- Content publication
expired_at TIMESTAMP,           -- For time-limited data
processed_at TIMESTAMP          -- For workflow tracking
```

#### Versioning and Audit Fields
For tables requiring change tracking:
```sql
version INTEGER DEFAULT 1,                    -- Optimistic locking
created_by VARCHAR(100),                      -- User/system identifier
updated_by VARCHAR(100),                      -- Last modifier
metadata TEXT DEFAULT '{}',                   -- Additional JSON data
notes TEXT                                    -- Human-readable notes
```

#### Soft Delete Pattern
For entities that should be archived rather than deleted:
```sql
is_deleted BOOLEAN DEFAULT FALSE,
deleted_at TIMESTAMP,
deleted_by VARCHAR(100),
deletion_reason TEXT
```

#### Status Fields
Standard status pattern with constraints:
```sql
status VARCHAR(50) DEFAULT 'pending',
CONSTRAINT chk_{table}_status CHECK (status IN ('pending', 'active', 'completed', 'failed', 'cancelled'))
```

### 4. **Foreign Key Standards**

#### Foreign Key Declarations
```sql
-- Standard foreign key with cascade
FOREIGN KEY (platform_id) REFERENCES platforms(id) ON DELETE CASCADE

-- Foreign key with set null (for optional references)
FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL

-- Foreign key with restrict (prevent deletion of referenced records)
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
```

#### Cascade Rules by Relationship Type
- **Ownership relationships**: `ON DELETE CASCADE`
  - content → content_metadata
  - downloads → download_sessions
- **Reference relationships**: `ON DELETE SET NULL`
  - content → parent_content
  - downloads → quality_options
- **Critical references**: `ON DELETE RESTRICT`
  - content → platforms (shouldn't delete platforms with content)

### 5. **Index Naming and Strategy**

#### Performance Indexes
```sql
-- Single column indexes
CREATE INDEX idx_{table}_{column} ON {table}({column});

-- Multi-column indexes (order matters!)
CREATE INDEX idx_{table}_{col1}_{col2} ON {table}({col1}, {col2});

-- Partial indexes for filtered queries
CREATE INDEX idx_{table}_{column}_active ON {table}({column}) 
WHERE is_active = TRUE;

-- Unique indexes
CREATE UNIQUE INDEX uq_{table}_{column} ON {table}({column});
```

#### Index Priority Guidelines
1. **Foreign keys** - Always indexed
2. **Status columns** - High priority for workflow queries
3. **Timestamp columns** - For date range queries
4. **Search columns** - Names, titles, descriptions
5. **Compound indexes** - For common multi-column WHERE clauses

### 6. **Data Validation Standards**

#### Check Constraints
```sql
-- Non-empty text fields
CONSTRAINT chk_{table}_{field}_not_empty CHECK (LENGTH(TRIM({field})) > 0)

-- Positive numbers
CONSTRAINT chk_{table}_{field}_positive CHECK ({field} >= 0)

-- Valid URLs
CONSTRAINT chk_{table}_url_format CHECK ({url_field} LIKE 'http%://%')

-- Enum values
CONSTRAINT chk_{table}_status CHECK (status IN ('value1', 'value2', 'value3'))

-- Range validations
CONSTRAINT chk_{table}_percentage CHECK (percentage >= 0 AND percentage <= 100)
```

#### Data Type Validation
```sql
-- JSON validation
CONSTRAINT chk_{table}_json CHECK (json_valid({json_field}))

-- Date format validation (for text dates)
CONSTRAINT chk_{table}_date_format CHECK ({date_field} LIKE '____-__-__')

-- Email format (basic)
CONSTRAINT chk_{table}_email CHECK ({email_field} LIKE '%@%.%')
```

### 7. **Standard Table Patterns**

#### Reference/Lookup Tables
```sql
CREATE TABLE {reference_name} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200),
    description TEXT,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_{table}_name_not_empty CHECK (LENGTH(TRIM(name)) > 0)
);
```

#### Main Entity Tables
```sql
CREATE TABLE {entity_name} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Core business fields
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Relationships
    parent_id INTEGER,
    category_id INTEGER,
    
    -- Status and workflow
    status VARCHAR(50) DEFAULT 'pending',
    
    -- Metrics (if applicable)
    usage_count INTEGER DEFAULT 0,
    
    -- Standard audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,
    is_deleted BOOLEAN DEFAULT FALSE,
    
    -- Foreign keys
    FOREIGN KEY (parent_id) REFERENCES {entity_name}(id) ON DELETE SET NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
    
    -- Constraints
    CONSTRAINT chk_{table}_name_not_empty CHECK (LENGTH(TRIM(name)) > 0),
    CONSTRAINT chk_{table}_status CHECK (status IN (...)),
    CONSTRAINT chk_{table}_usage_count CHECK (usage_count >= 0)
);
```

#### Junction Tables (Many-to-Many)
```sql
CREATE TABLE {table1}_{table2} (
    {table1}_id INTEGER NOT NULL,
    {table2}_id INTEGER NOT NULL,
    
    -- Relationship metadata
    assigned_by VARCHAR(50) DEFAULT 'user',
    weight DECIMAL(5,2) DEFAULT 1.0,
    is_primary BOOLEAN DEFAULT FALSE,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    
    -- Primary key
    PRIMARY KEY ({table1}_id, {table2}_id),
    
    -- Foreign keys
    FOREIGN KEY ({table1}_id) REFERENCES {table1}(id) ON DELETE CASCADE,
    FOREIGN KEY ({table2}_id) REFERENCES {table2}(id) ON DELETE CASCADE
);
```

### 8. **Trigger Standards**

#### Automatic Timestamp Updates
```sql
CREATE TRIGGER update_{table}_timestamp
    AFTER UPDATE ON {table}
    FOR EACH ROW
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE {table} SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
```

#### Audit Trail Triggers
```sql
CREATE TRIGGER {table}_audit_insert
    AFTER INSERT ON {table}
    FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_at)
    VALUES ('{table}', NEW.id, 'INSERT', NULL, json_object(...), CURRENT_TIMESTAMP);
END;
```

#### Data Validation Triggers
```sql
CREATE TRIGGER validate_{table}_{field}
    BEFORE INSERT ON {table}
    FOR EACH ROW
    WHEN {validation_condition}
BEGIN
    SELECT RAISE(ABORT, 'Validation error: {error_message}');
END;
```

## Implementation Guidelines

### 1. **Schema Evolution Strategy**

#### Migration Scripts
- Each schema change MUST have a migration script
- Migration scripts MUST be reversible where possible
- Version migrations using semantic versioning
- Include rollback instructions in migration comments

#### Backward Compatibility
- Avoid breaking changes to existing columns
- Add new columns with DEFAULT values
- Use views to maintain legacy interfaces
- Deprecation warnings before removal

### 2. **Performance Considerations**

#### Index Strategy
- Create indexes AFTER bulk data loading
- Monitor query performance with EXPLAIN QUERY PLAN
- Remove unused indexes
- Consider composite indexes for common WHERE clauses

#### Data Types
- Use appropriate data types for storage efficiency
- Consider INTEGER timestamps vs. TEXT dates
- Use BLOB sparingly (prefer file paths)
- Normalize repeated text values into lookup tables

### 3. **Security Standards**

#### Data Protection
- No sensitive data in database logs
- Use parameterized queries only
- Validate all input data
- Consider field-level encryption for sensitive data

#### Access Control
- Principle of least privilege
- Separate read/write access patterns
- Audit critical operations
- Use application-level authorization

### 4. **Documentation Requirements**

#### Table Documentation
Each table MUST have:
- Purpose and business context
- Relationship descriptions
- Data retention policies
- Performance characteristics
- Example queries

#### Column Documentation
Critical columns need:
- Business meaning and constraints
- Data source and update frequency
- Validation rules
- Usage examples

## Schema Compliance Checklist

### New Table Checklist
- [ ] Follows naming conventions
- [ ] Has appropriate primary key
- [ ] Includes standard timestamp fields
- [ ] Has proper foreign key constraints
- [ ] Includes necessary check constraints
- [ ] Has performance indexes
- [ ] Includes documentation
- [ ] Has update timestamp trigger
- [ ] Follows data type standards

### Data Integrity Checklist
- [ ] All foreign keys have proper cascade rules
- [ ] Check constraints validate business rules
- [ ] Unique constraints prevent duplicates
- [ ] Default values are appropriate
- [ ] NULL handling is explicit
- [ ] Triggers maintain data consistency

### Performance Checklist
- [ ] Query patterns identified
- [ ] Appropriate indexes created
- [ ] Partial indexes for filtered queries
- [ ] Composite indexes for multi-column searches
- [ ] Index maintenance strategy
- [ ] Performance testing completed

This standardization ensures consistency, maintainability, and performance across the entire Social Download Manager v2.0 database schema. 