#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Import Structure Validator for UI Migration
Validates import dependencies and module paths during migration from v1.2.1 to v2.0
Part of subtask 32.7 - Import Structure Change Validation
"""

import sys
import os
import ast
import importlib
import importlib.util
import json
import re
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import traceback

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


@dataclass
class ImportDependency:
    """Represents an import dependency"""
    source_file: str
    import_type: str  # 'import', 'from_import', 'relative'
    module_name: str
    imported_names: List[str]
    line_number: int
    is_relative: bool
    resolved_path: Optional[str] = None


@dataclass
class ImportValidationResult:
    """Result of import validation"""
    file_path: str
    total_imports: int
    valid_imports: int
    broken_imports: int
    import_dependencies: List[ImportDependency]
    errors: List[str]
    warnings: List[str]
    migration_issues: List[str]


@dataclass
class ImportMigrationPlan:
    """Migration plan for import changes"""
    legacy_import: str
    new_import: str
    affected_files: List[str]
    migration_type: str  # 'rename', 'relocate', 'adapter_bridge', 'split'
    priority: str  # 'critical', 'high', 'medium', 'low'


@dataclass
class ImportStructureReport:
    """Comprehensive import structure report"""
    total_files: int
    analyzed_files: int
    total_imports: int
    valid_imports: int
    broken_imports: int
    migration_required: int
    validation_results: List[ImportValidationResult]
    migration_plans: List[ImportMigrationPlan]
    recommendations: List[str]


class ImportStructureValidator:
    """Validator for import structure during UI migration"""
    
    def __init__(self):
        self.project_root = project_root
        self.python_files: List[str] = []
        self.import_graph: Dict[str, List[ImportDependency]] = {}
        self.broken_imports: List[ImportDependency] = []
        self.migration_mappings = self._define_migration_mappings()
        
        # Patterns for different import types
        self.import_patterns = {
            'ui_legacy': r'^ui\.(?!components|adapters)',
            'ui_v2': r'^ui\.components',
            'ui_adapters': r'^ui\.adapters',
            'localization': r'^localization',
            'platforms': r'^platforms',
            'core': r'^core',
            'utils': r'^utils'
        }
        
        # Files to analyze
        self.target_directories = [
            'ui',
            'core',
            'platforms',
            'localization',
            'utils',
            'tests',
            'scripts_dev'
        ]
        
    def _define_migration_mappings(self) -> Dict[str, ImportMigrationPlan]:
        """Define mappings for import migration"""
        return {
            'ui.video_info_tab': ImportMigrationPlan(
                legacy_import='ui.video_info_tab',
                new_import='ui.adapters.video_info_tab_adapter',
                affected_files=[],
                migration_type='adapter_bridge',
                priority='critical'
            ),
            'ui.downloaded_videos_tab': ImportMigrationPlan(
                legacy_import='ui.downloaded_videos_tab',
                new_import='ui.adapters.downloaded_videos_tab_adapter',
                affected_files=[],
                migration_type='adapter_bridge',
                priority='critical'
            ),
            'ui.main_window': ImportMigrationPlan(
                legacy_import='ui.main_window',
                new_import='ui.main_window',  # No change for main window
                affected_files=[],
                migration_type='rename',
                priority='medium'
            )
        }
        
    def discover_python_files(self) -> List[str]:
        """Discover all Python files in target directories"""
        python_files = []
        
        for directory in self.target_directories:
            dir_path = os.path.join(self.project_root, directory)
            if os.path.exists(dir_path):
                for root, dirs, files in os.walk(dir_path):
                    # Skip __pycache__ directories
                    dirs[:] = [d for d in dirs if d != '__pycache__']
                    
                    for file in files:
                        if file.endswith('.py'):
                            file_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_path, self.project_root)
                            python_files.append(rel_path)
                            
        # Add main.py if exists
        main_py = os.path.join(self.project_root, 'main.py')
        if os.path.exists(main_py):
            python_files.append('main.py')
            
        self.python_files = python_files
        print(f"Discovered {len(python_files)} Python files")
        return python_files
        
    def extract_imports_from_file(self, file_path: str) -> List[ImportDependency]:
        """Extract all imports from a Python file using AST"""
        full_path = os.path.join(self.project_root, file_path)
        imports = []
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content, filename=file_path)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(ImportDependency(
                            source_file=file_path,
                            import_type='import',
                            module_name=alias.name,
                            imported_names=[alias.asname or alias.name],
                            line_number=node.lineno,
                            is_relative=False
                        ))
                        
                elif isinstance(node, ast.ImportFrom):
                    module_name = node.module or ''
                    imported_names = []
                    
                    for alias in node.names:
                        imported_names.append(alias.asname or alias.name)
                        
                    imports.append(ImportDependency(
                        source_file=file_path,
                        import_type='from_import',
                        module_name=module_name,
                        imported_names=imported_names,
                        line_number=node.lineno,
                        is_relative=node.level > 0
                    ))
                    
        except Exception as e:
            print(f"Error parsing {file_path}: {str(e)}")
            
        return imports
        
    def validate_import_dependency(self, dependency: ImportDependency) -> Tuple[bool, Optional[str], List[str]]:
        """Validate a single import dependency"""
        errors = []
        warnings = []
        is_valid = True
        resolved_path = None
        
        try:
            module_name = dependency.module_name
            
            # Handle relative imports
            if dependency.is_relative:
                # Convert relative import to absolute
                source_dir = os.path.dirname(dependency.source_file)
                module_name = self._resolve_relative_import(module_name, source_dir, dependency.line_number)
                
            # Try to resolve the module
            try:
                spec = importlib.util.find_spec(module_name)
                if spec is not None:
                    resolved_path = spec.origin
                    is_valid = True
                else:
                    is_valid = False
                    errors.append(f"Module '{module_name}' not found")
                    
            except (ImportError, ModuleNotFoundError, ValueError) as e:
                is_valid = False
                errors.append(f"Import error for '{module_name}': {str(e)}")
                
            # Check for migration requirements
            migration_warnings = self._check_migration_requirements(dependency)
            warnings.extend(migration_warnings)
            
            # Validate imported names
            if is_valid and dependency.import_type == 'from_import':
                name_errors = self._validate_imported_names(module_name, dependency.imported_names)
                if name_errors:
                    errors.extend(name_errors)
                    is_valid = False
                    
        except Exception as e:
            is_valid = False
            errors.append(f"Validation error: {str(e)}")
            
        dependency.resolved_path = resolved_path
        return is_valid, resolved_path, errors + warnings
        
    def _resolve_relative_import(self, module_name: str, source_dir: str, level: int) -> str:
        """Resolve relative import to absolute module name"""
        # Convert file path to module path
        source_module_parts = source_dir.replace('/', '.').replace('\\', '.').split('.')
        
        # Go up 'level' directories
        for _ in range(level):
            if source_module_parts:
                source_module_parts.pop()
                
        # Combine with relative module name
        if module_name:
            return '.'.join(source_module_parts + [module_name])
        else:
            return '.'.join(source_module_parts)
            
    def _check_migration_requirements(self, dependency: ImportDependency) -> List[str]:
        """Check if import requires migration"""
        warnings = []
        module_name = dependency.module_name
        
        # Check against migration mappings
        for legacy_import, migration_plan in self.migration_mappings.items():
            if module_name == legacy_import or module_name.startswith(legacy_import + '.'):
                warnings.append(f"Import '{module_name}' requires migration to '{migration_plan.new_import}'")
                migration_plan.affected_files.append(dependency.source_file)
                
        # Check for UI legacy patterns
        if re.match(self.import_patterns['ui_legacy'], module_name):
            warnings.append(f"Legacy UI import '{module_name}' may need updating for v2.0 compatibility")
            
        return warnings
        
    def _validate_imported_names(self, module_name: str, imported_names: List[str]) -> List[str]:
        """Validate that imported names exist in the module"""
        errors = []
        
        try:
            module = importlib.import_module(module_name)
            
            for name in imported_names:
                if name == '*':
                    continue  # Skip wildcard imports
                    
                if not hasattr(module, name):
                    errors.append(f"Name '{name}' not found in module '{module_name}'")
                    
        except Exception as e:
            errors.append(f"Cannot validate names in '{module_name}': {str(e)}")
            
        return errors
        
    def validate_file_imports(self, file_path: str) -> ImportValidationResult:
        """Validate all imports in a single file"""
        imports = self.extract_imports_from_file(file_path)
        self.import_graph[file_path] = imports
        
        valid_count = 0
        broken_count = 0
        errors = []
        warnings = []
        migration_issues = []
        
        for dependency in imports:
            is_valid, resolved_path, issues = self.validate_import_dependency(dependency)
            
            if is_valid:
                valid_count += 1
            else:
                broken_count += 1
                self.broken_imports.append(dependency)
                
            # Categorize issues
            for issue in issues:
                if 'migration' in issue.lower() or 'requires' in issue.lower():
                    migration_issues.append(issue)
                elif 'not found' in issue.lower() or 'error' in issue.lower():
                    errors.append(issue)
                else:
                    warnings.append(issue)
                    
        return ImportValidationResult(
            file_path=file_path,
            total_imports=len(imports),
            valid_imports=valid_count,
            broken_imports=broken_count,
            import_dependencies=imports,
            errors=errors,
            warnings=warnings,
            migration_issues=migration_issues
        )
        
    def run_comprehensive_validation(self) -> ImportStructureReport:
        """Run comprehensive import structure validation"""
        print("Starting comprehensive import structure validation...")
        
        # Discover files
        python_files = self.discover_python_files()
        
        # Validate each file
        validation_results = []
        
        for file_path in python_files:
            print(f"Validating imports in: {file_path}")
            
            try:
                result = self.validate_file_imports(file_path)
                validation_results.append(result)
            except Exception as e:
                print(f"Error validating {file_path}: {str(e)}")
                # Create error result
                error_result = ImportValidationResult(
                    file_path=file_path,
                    total_imports=0,
                    valid_imports=0,
                    broken_imports=0,
                    import_dependencies=[],
                    errors=[f"Validation failed: {str(e)}"],
                    warnings=[],
                    migration_issues=[]
                )
                validation_results.append(error_result)
                
        # Generate migration plans
        migration_plans = self._generate_migration_plans()
        
        # Create comprehensive report
        report = self._generate_structure_report(validation_results, migration_plans)
        
        print(f"Import validation complete. {report.valid_imports}/{report.total_imports} imports valid")
        return report
        
    def _generate_migration_plans(self) -> List[ImportMigrationPlan]:
        """Generate migration plans based on validation results"""
        plans = list(self.migration_mappings.values())
        
        # Add additional plans based on discovered issues
        for file_path, imports in self.import_graph.items():
            for dependency in imports:
                module_name = dependency.module_name
                
                # Check for patterns that need migration
                if re.match(self.import_patterns['ui_legacy'], module_name):
                    # Check if we already have a plan for this
                    existing_plan = next((p for p in plans if p.legacy_import == module_name), None)
                    if not existing_plan:
                        # Create new migration plan
                        new_plan = ImportMigrationPlan(
                            legacy_import=module_name,
                            new_import=self._suggest_new_import_path(module_name),
                            affected_files=[file_path],
                            migration_type='relocate',
                            priority='medium'
                        )
                        plans.append(new_plan)
                    else:
                        if file_path not in existing_plan.affected_files:
                            existing_plan.affected_files.append(file_path)
                            
        return plans
        
    def _suggest_new_import_path(self, legacy_import: str) -> str:
        """Suggest new import path for legacy imports"""
        if legacy_import.startswith('ui.'):
            component_name = legacy_import.split('.')[-1]
            
            # Check if it's a tab component
            if 'tab' in component_name:
                return f'ui.components.tabs.{component_name}'
            else:
                return f'ui.components.{component_name}'
        
        return legacy_import  # No change suggested
        
    def _generate_structure_report(self, results: List[ImportValidationResult], 
                                 plans: List[ImportMigrationPlan]) -> ImportStructureReport:
        """Generate comprehensive import structure report"""
        
        total_files = len(results)
        analyzed_files = len([r for r in results if r.total_imports > 0])
        total_imports = sum(r.total_imports for r in results)
        valid_imports = sum(r.valid_imports for r in results)
        broken_imports = sum(r.broken_imports for r in results)
        migration_required = len([r for r in results if r.migration_issues])
        
        # Generate recommendations
        recommendations = self._generate_recommendations(results, plans)
        
        return ImportStructureReport(
            total_files=total_files,
            analyzed_files=analyzed_files,
            total_imports=total_imports,
            valid_imports=valid_imports,
            broken_imports=broken_imports,
            migration_required=migration_required,
            validation_results=results,
            migration_plans=plans,
            recommendations=recommendations
        )
        
    def _generate_recommendations(self, results: List[ImportValidationResult],
                                plans: List[ImportMigrationPlan]) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Critical issues
        critical_files = [r for r in results if r.errors]
        if critical_files:
            recommendations.append(f"Fix broken imports in {len(critical_files)} files before migration")
            
        # Migration requirements
        migration_files = [r for r in results if r.migration_issues]
        if migration_files:
            recommendations.append(f"Update imports in {len(migration_files)} files for v2.0 compatibility")
            
        # Priority-based recommendations
        critical_plans = [p for p in plans if p.priority == 'critical']
        if critical_plans:
            recommendations.append(f"Address {len(critical_plans)} critical import migrations immediately")
            
        # Pattern-based recommendations
        ui_legacy_count = sum(1 for r in results for d in r.import_dependencies 
                             if re.match(self.import_patterns['ui_legacy'], d.module_name))
        if ui_legacy_count > 0:
            recommendations.append(f"Modernize {ui_legacy_count} legacy UI imports to v2.0 architecture")
            
        # Circular dependency detection
        circular_deps = self._detect_circular_dependencies()
        if circular_deps:
            recommendations.append(f"Resolve {len(circular_deps)} circular import dependencies")
            
        if not recommendations:
            recommendations.append("All imports are valid and migration-ready!")
            
        return recommendations
        
    def _detect_circular_dependencies(self) -> List[List[str]]:
        """Detect circular import dependencies"""
        circular_deps = []
        
        # Build dependency graph
        dep_graph = {}
        for file_path, imports in self.import_graph.items():
            deps = []
            for imp in imports:
                # Convert module name to file path (simplified)
                module_file = imp.module_name.replace('.', '/') + '.py'
                if module_file in self.python_files:
                    deps.append(module_file)
            dep_graph[file_path] = deps
            
        # Simple cycle detection (DFS-based)
        visited = set()
        rec_stack = set()
        
        def has_cycle(node, path):
            if node in rec_stack:
                # Found cycle
                cycle_start = path.index(node)
                return path[cycle_start:]
            if node in visited:
                return None
                
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in dep_graph.get(node, []):
                cycle = has_cycle(neighbor, path.copy())
                if cycle:
                    return cycle
                    
            rec_stack.remove(node)
            return None
            
        for file_path in dep_graph:
            if file_path not in visited:
                cycle = has_cycle(file_path, [])
                if cycle:
                    circular_deps.append(cycle)
                    
        return circular_deps
        
    def generate_migration_script(self, plans: List[ImportMigrationPlan]) -> str:
        """Generate Python script to automate import migrations"""
        
        script_lines = [
            "#!/usr/bin/env python3",
            "# -*- coding: utf-8 -*-",
            "",
            "\"\"\"",
            "Automated Import Migration Script",
            "Generated by ImportStructureValidator",
            "\"\"\"",
            "",
            "import os",
            "import re",
            "import sys",
            "",
            "def migrate_imports_in_file(file_path, migrations):",
            "    \"\"\"Migrate imports in a single file\"\"\"",
            "    with open(file_path, 'r', encoding='utf-8') as f:",
            "        content = f.read()",
            "    ",
            "    original_content = content",
            "    ",
            "    for old_import, new_import in migrations.items():",
            "        # Handle 'import' statements",
            "        content = re.sub(",
            "            rf'import {re.escape(old_import)}\\b',",
            "            f'import {new_import}',",
            "            content",
            "        )",
            "        ",
            "        # Handle 'from ... import' statements",
            "        content = re.sub(",
            "            rf'from {re.escape(old_import)}\\b',",
            "            f'from {new_import}',",
            "            content",
            "        )",
            "    ",
            "    if content != original_content:",
            "        with open(file_path, 'w', encoding='utf-8') as f:",
            "            f.write(content)",
            "        print(f'Updated imports in: {file_path}')",
            "    ",
            "",
            "def main():",
            "    \"\"\"Main migration function\"\"\"",
            "    migrations = {"
        ]
        
        # Add migration mappings
        for plan in plans:
            if plan.migration_type in ['adapter_bridge', 'relocate', 'rename']:
                script_lines.append(f"        '{plan.legacy_import}': '{plan.new_import}',")
                
        script_lines.extend([
            "    }",
            "    ",
            "    files_to_migrate = [",
        ])
        
        # Add affected files
        all_files = set()
        for plan in plans:
            all_files.update(plan.affected_files)
            
        for file_path in sorted(all_files):
            script_lines.append(f"        '{file_path}',")
            
        script_lines.extend([
            "    ]",
            "    ",
            "    for file_path in files_to_migrate:",
            "        if os.path.exists(file_path):",
            "            migrate_imports_in_file(file_path, migrations)",
            "        else:",
            "            print(f'File not found: {file_path}')",
            "    ",
            "    print('Import migration completed!')",
            "",
            "if __name__ == '__main__':",
            "    main()"
        ])
        
        return '\n'.join(script_lines)
        
    def save_report(self, report: ImportStructureReport, filepath: str):
        """Save import structure report to file"""
        
        report_dict = asdict(report)
        
        # Add metadata
        report_dict["metadata"] = {
            "validator_version": "1.0.0",
            "validation_timestamp": "2025-06-03T12:00:00Z",
            "project_root": self.project_root,
            "target_directories": self.target_directories,
            "migration_mappings": len(self.migration_mappings),
            "import_patterns": self.import_patterns
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
            
        print(f"Import structure report saved to: {filepath}")
        
    def print_summary(self, report: ImportStructureReport):
        """Print summary of import validation results"""
        
        print("\n" + "="*60)
        print("IMPORT STRUCTURE VALIDATION SUMMARY")
        print("="*60)
        
        print(f"Files Analyzed: {report.analyzed_files}/{report.total_files}")
        print(f"Total Imports: {report.total_imports}")
        print(f"Valid Imports: {report.valid_imports}")
        print(f"Broken Imports: {report.broken_imports}")
        print(f"Migration Required: {report.migration_required} files")
        print(f"Import Success Rate: {(report.valid_imports/report.total_imports)*100:.1f}%")
        
        print(f"\nMIGRATION PLANS:")
        for plan in report.migration_plans:
            print(f"  [{plan.priority.upper()}] {plan.legacy_import} → {plan.new_import}")
            print(f"    Type: {plan.migration_type}, Files: {len(plan.affected_files)}")
            
        print(f"\nRECOMMENDATIONS:")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"{i}. {rec}")
            
        print(f"\nCRITICAL ISSUES:")
        critical_results = [r for r in report.validation_results if r.errors]
        for result in critical_results[:5]:  # Show first 5
            print(f"  {result.file_path}: {len(result.errors)} errors")
            for error in result.errors[:2]:  # Show first 2 errors
                print(f"    - {error}")


if __name__ == "__main__":
    """Direct execution for testing"""
    
    validator = ImportStructureValidator()
    report = validator.run_comprehensive_validation()
    
    # Print summary
    validator.print_summary(report)
    
    # Save detailed report
    report_path = os.path.join(project_root, "tests", "ui_migration", "import_structure_report.json")
    validator.save_report(report, report_path)
    
    # Generate migration script
    migration_script = validator.generate_migration_script(report.migration_plans)
    script_path = os.path.join(project_root, "scripts_dev", "migration", "auto_import_migration.py")
    
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(migration_script)
        
    print(f"\nValidation complete. Success rate: {(report.valid_imports/report.total_imports)*100:.1f}%")
    print(f"Migration script generated: {script_path}") 