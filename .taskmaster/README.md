# Task Master Project Files

## 📁 Directory Structure

This directory contains Task Master AI project management files for Social Download Manager v2.0.

### 🟢 Shared Files (Included in Git)

#### `/templates/`
- **Purpose:** Template files for new projects
- **Contents:** Standard task templates, workflow templates
- **Why Share:** Helps team members set up consistent project structure

#### `/docs/`
- **Purpose:** Documentation and guidelines
- **Contents:** Workflow guides, best practices, task examples
- **Why Share:** Team knowledge and onboarding resources

#### `README.md` (this file)
- **Purpose:** Documentation about taskmaster setup
- **Why Share:** Explains the system to team members

### 🔴 Private Files (Excluded from Git)

#### `/tasks/`
- **Contents:** Individual task files, tasks.json, backup files
- **Why Private:** Personal/local task instances, work progress
- **Note:** These are generated from your specific project workflow

#### `/reports/`
- **Contents:** Complexity analysis reports, performance reports
- **Why Private:** Local analysis results specific to your environment

#### `config.json`
- **Contents:** Local taskmaster configuration
- **Why Private:** Personal preferences and local paths

## 🛠️ Setup Instructions

### For New Team Members:

1. **Initialize Taskmaster:**
   ```bash
   npm install -g task-master-ai
   task-master init
   ```

2. **Configure Your Environment:**
   ```bash
   task-master models --setup
   ```

3. **Start with Project PRD:**
   ```bash
   task-master parse-prd --input=".taskmaster/docs/prd.txt"
   ```

### For Existing Team Members:

- **Tasks and reports are personal** - don't expect to see others' task instances
- **Templates and docs are shared** - contribute improvements here
- **Follow the workflow documented** in `/docs/`

## 📝 Best Practices

### ✅ Do Share:
- Template improvements
- Workflow documentation
- Best practice guides
- Example configurations

### ❌ Don't Share:
- Personal task instances
- Local configuration files
- Analysis reports
- Work-in-progress task files

## 🔄 Workflow Integration

This setup allows:
- **Individual task management** without conflicts
- **Shared team knowledge** and standards
- **Consistent project structure** across team
- **Personal productivity** with team collaboration

## 🆘 Troubleshooting

### Missing Templates/Docs:
```bash
git checkout HEAD -- .taskmaster/templates/
git checkout HEAD -- .taskmaster/docs/
```

### Reset Local Taskmaster:
```bash
rm -rf .taskmaster/tasks/
rm -rf .taskmaster/reports/
rm .taskmaster/config.json
task-master init
```

---

**Note:** This structure ensures team collaboration while maintaining personal productivity workflows. 