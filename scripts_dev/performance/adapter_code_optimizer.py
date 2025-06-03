#!/usr/bin/env python3
"""
Adapter Framework Code Optimization and Refactoring System
==========================================================

This module provides comprehensive code analysis and optimization including:
- Code quality analysis and metrics
- Performance bottleneck detection
- Code duplication identification
- Design pattern optimization
- Algorithm efficiency improvements
- Maintainability and scalability assessment
- Automated refactoring suggestions
"""

import ast
import gc
import json
import logging
import os
import re
import sys
import time
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
import inspect
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CodeMetrics:
    """Code quality and complexity metrics"""
    lines_of_code: int = 0
    cyclomatic_complexity: int = 0
    cognitive_complexity: int = 0
    maintainability_index: float = 0.0
    code_duplication_ratio: float = 0.0
    test_coverage: float = 0.0
    dependency_count: int = 0
    class_count: int = 0
    function_count: int = 0
    comment_ratio: float = 0.0


@dataclass
class PerformanceBottleneck:
    """Performance bottleneck information"""
    location: str
    type: str  # 'algorithm', 'io', 'memory', 'cpu'
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    suggested_fix: str
    estimated_improvement: str


@dataclass
class CodeDuplication:
    """Code duplication detection result"""
    file1: str
    file2: str
    line_start_1: int
    line_end_1: int
    line_start_2: int
    line_end_2: int
    similarity_score: float
    duplicate_lines: int
    code_snippet: str


@dataclass
class RefactoringOpportunity:
    """Refactoring opportunity identification"""
    location: str
    type: str  # 'extract_method', 'extract_class', 'simplify_condition', etc.
    description: str
    current_code: str
    suggested_code: str
    benefits: List[str]
    effort_estimate: str  # 'low', 'medium', 'high'


@dataclass
class OptimizationResult:
    """Comprehensive optimization analysis result"""
    timestamp: datetime = field(default_factory=datetime.now)
    total_files_analyzed: int = 0
    code_metrics: CodeMetrics = field(default_factory=CodeMetrics)
    performance_bottlenecks: List[PerformanceBottleneck] = field(default_factory=list)
    code_duplications: List[CodeDuplication] = field(default_factory=list)
    refactoring_opportunities: List[RefactoringOpportunity] = field(default_factory=list)
    optimization_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)


class CodeAnalyzer:
    """Advanced code analysis and quality assessment"""
    
    def __init__(self):
        self.analyzed_files = []
        self.ast_cache = {}
        
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a single Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            self.ast_cache[file_path] = tree
            
            metrics = self._calculate_file_metrics(content, tree)
            bottlenecks = self._detect_performance_issues(tree, file_path)
            
            return {
                'file_path': file_path,
                'metrics': metrics,
                'bottlenecks': bottlenecks,
                'content': content,
                'ast': tree
            }
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return {
                'file_path': file_path,
                'error': str(e),
                'metrics': CodeMetrics(),
                'bottlenecks': [],
                'content': '',
                'ast': None
            }
    
    def _calculate_file_metrics(self, content: str, tree: ast.AST) -> CodeMetrics:
        """Calculate various code metrics for a file"""
        lines = content.split('\n')
        
        metrics = CodeMetrics()
        metrics.lines_of_code = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
        
        # Count different AST node types
        class_count = 0
        function_count = 0
        comment_lines = 0
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#') or '"""' in stripped or "'''" in stripped:
                comment_lines += 1
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_count += 1
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_count += 1
        
        metrics.class_count = class_count
        metrics.function_count = function_count
        metrics.comment_ratio = comment_lines / len(lines) if lines else 0
        
        # Calculate cyclomatic complexity (simplified)
        metrics.cyclomatic_complexity = self._calculate_cyclomatic_complexity(tree)
        
        # Calculate cognitive complexity (simplified)
        metrics.cognitive_complexity = self._calculate_cognitive_complexity(tree)
        
        # Calculate maintainability index (simplified version)
        metrics.maintainability_index = self._calculate_maintainability_index(metrics)
        
        return metrics
    
    def _calculate_cyclomatic_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity (simplified)"""
        complexity = 1  # Base complexity
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.Try):
                complexity += len(node.handlers)
            elif isinstance(node, (ast.BoolOp, ast.Compare)):
                complexity += 1
        
        return complexity
    
    def _calculate_cognitive_complexity(self, tree: ast.AST) -> int:
        """Calculate cognitive complexity (simplified)"""
        complexity = 0
        nesting_level = 0
        
        class CognitiveComplexityVisitor(ast.NodeVisitor):
            def __init__(self):
                self.complexity = 0
                self.nesting_level = 0
            
            def visit_If(self, node):
                self.complexity += 1 + self.nesting_level
                self.nesting_level += 1
                self.generic_visit(node)
                self.nesting_level -= 1
            
            def visit_While(self, node):
                self.complexity += 1 + self.nesting_level
                self.nesting_level += 1
                self.generic_visit(node)
                self.nesting_level -= 1
            
            def visit_For(self, node):
                self.complexity += 1 + self.nesting_level
                self.nesting_level += 1
                self.generic_visit(node)
                self.nesting_level -= 1
        
        visitor = CognitiveComplexityVisitor()
        visitor.visit(tree)
        return visitor.complexity
    
    def _calculate_maintainability_index(self, metrics: CodeMetrics) -> float:
        """Calculate maintainability index (simplified)"""
        # Simplified version of the maintainability index
        if metrics.lines_of_code == 0:
            return 100.0
        
        # Formula: 171 - 5.2 * ln(V) - 0.23 * CC - 16.2 * ln(LOC)
        # Where V is volume, CC is cyclomatic complexity, LOC is lines of code
        # Simplified approximation
        volume = metrics.lines_of_code * 0.5  # Simplified volume calculation
        cc = metrics.cyclomatic_complexity
        loc = metrics.lines_of_code
        
        if volume <= 0 or loc <= 0:
            return 100.0
        
        import math
        mi = 171 - 5.2 * math.log(volume) - 0.23 * cc - 16.2 * math.log(loc)
        return max(0, min(100, mi))
    
    def _detect_performance_issues(self, tree: ast.AST, file_path: str) -> List[PerformanceBottleneck]:
        """Detect potential performance bottlenecks"""
        bottlenecks = []
        
        for node in ast.walk(tree):
            # Nested loops detection
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(node):
                    if child != node and isinstance(child, (ast.For, ast.While)):
                        bottlenecks.append(PerformanceBottleneck(
                            location=f"{file_path}:line {node.lineno}",
                            type="algorithm",
                            severity="medium",
                            description="Nested loops detected - potential O(n²) complexity",
                            suggested_fix="Consider optimizing with hash maps, sets, or different algorithm",
                            estimated_improvement="20-80% performance improvement"
                        ))
                        break
            
            # Large list comprehensions
            if isinstance(node, ast.ListComp):
                if len(list(ast.walk(node))) > 10:  # Complex comprehension
                    bottlenecks.append(PerformanceBottleneck(
                        location=f"{file_path}:line {node.lineno}",
                        type="memory",
                        severity="low",
                        description="Complex list comprehension detected",
                        suggested_fix="Consider using generator expressions or breaking into steps",
                        estimated_improvement="10-30% memory reduction"
                    ))
            
            # String concatenation in loops
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(node):
                    if isinstance(child, ast.AugAssign) and isinstance(child.op, ast.Add):
                        if isinstance(child.target, ast.Name):
                            bottlenecks.append(PerformanceBottleneck(
                                location=f"{file_path}:line {child.lineno}",
                                type="algorithm",
                                severity="medium",
                                description="String concatenation in loop detected",
                                suggested_fix="Use join() or f-strings for better performance",
                                estimated_improvement="50-200% performance improvement"
                            ))
        
        return bottlenecks


class DuplicationDetector:
    """Code duplication detection and analysis"""
    
    def __init__(self, min_lines: int = 5, similarity_threshold: float = 0.8):
        self.min_lines = min_lines
        self.similarity_threshold = similarity_threshold
    
    def detect_duplications(self, file_contents: Dict[str, str]) -> List[CodeDuplication]:
        """Detect code duplications across files"""
        duplications = []
        
        file_items = list(file_contents.items())
        
        for i, (file1, content1) in enumerate(file_items):
            for j, (file2, content2) in enumerate(file_items[i+1:], i+1):
                file_duplications = self._compare_files(file1, content1, file2, content2)
                duplications.extend(file_duplications)
        
        return duplications
    
    def _compare_files(self, file1: str, content1: str, file2: str, content2: str) -> List[CodeDuplication]:
        """Compare two files for duplications"""
        duplications = []
        lines1 = content1.split('\n')
        lines2 = content2.split('\n')
        
        # Sliding window approach
        for i in range(len(lines1) - self.min_lines + 1):
            for j in range(len(lines2) - self.min_lines + 1):
                similarity, length = self._calculate_similarity(
                    lines1[i:i+self.min_lines],
                    lines2[j:j+self.min_lines]
                )
                
                if similarity >= self.similarity_threshold and length >= self.min_lines:
                    # Extend the match
                    extended_length = self._extend_match(lines1, lines2, i, j, length)
                    
                    duplications.append(CodeDuplication(
                        file1=file1,
                        file2=file2,
                        line_start_1=i + 1,
                        line_end_1=i + extended_length,
                        line_start_2=j + 1,
                        line_end_2=j + extended_length,
                        similarity_score=similarity,
                        duplicate_lines=extended_length,
                        code_snippet='\n'.join(lines1[i:i+extended_length][:3]) + '...'
                    ))
        
        return duplications
    
    def _calculate_similarity(self, lines1: List[str], lines2: List[str]) -> Tuple[float, int]:
        """Calculate similarity between two line sequences"""
        if not lines1 or not lines2:
            return 0.0, 0
        
        # Normalize lines (remove whitespace, comments)
        norm_lines1 = [self._normalize_line(line) for line in lines1]
        norm_lines2 = [self._normalize_line(line) for line in lines2]
        
        # Remove empty lines
        norm_lines1 = [line for line in norm_lines1 if line]
        norm_lines2 = [line for line in norm_lines2 if line]
        
        if not norm_lines1 or not norm_lines2:
            return 0.0, 0
        
        # Calculate similarity using Jaccard index
        set1 = set(norm_lines1)
        set2 = set(norm_lines2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        similarity = intersection / union if union > 0 else 0.0
        return similarity, min(len(norm_lines1), len(norm_lines2))
    
    def _normalize_line(self, line: str) -> str:
        """Normalize a line for comparison"""
        # Remove comments, extra whitespace
        line = re.sub(r'#.*$', '', line)  # Remove comments
        line = re.sub(r'\s+', ' ', line.strip())  # Normalize whitespace
        return line
    
    def _extend_match(self, lines1: List[str], lines2: List[str], 
                     start1: int, start2: int, initial_length: int) -> int:
        """Extend a match as far as possible"""
        length = initial_length
        max_len1 = len(lines1) - start1
        max_len2 = len(lines2) - start2
        max_extend = min(max_len1, max_len2)
        
        while length < max_extend:
            norm1 = self._normalize_line(lines1[start1 + length])
            norm2 = self._normalize_line(lines2[start2 + length])
            
            if norm1 == norm2 and norm1:  # Lines match and are not empty
                length += 1
            else:
                break
        
        return length


class RefactoringAnalyzer:
    """Refactoring opportunity detection and suggestions"""
    
    def __init__(self):
        pass
    
    def analyze_refactoring_opportunities(self, file_data: Dict[str, Any]) -> List[RefactoringOpportunity]:
        """Analyze code for refactoring opportunities"""
        opportunities = []
        
        for file_path, data in file_data.items():
            if 'ast' not in data or data['ast'] is None:
                continue
            
            tree = data['ast']
            content = data['content']
            
            # Detect long methods
            opportunities.extend(self._detect_long_methods(tree, file_path, content))
            
            # Detect large classes
            opportunities.extend(self._detect_large_classes(tree, file_path, content))
            
            # Detect complex conditions
            opportunities.extend(self._detect_complex_conditions(tree, file_path, content))
            
            # Detect magic numbers
            opportunities.extend(self._detect_magic_numbers(tree, file_path, content))
        
        return opportunities
    
    def _detect_long_methods(self, tree: ast.AST, file_path: str, content: str) -> List[RefactoringOpportunity]:
        """Detect methods that are too long"""
        opportunities = []
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                    method_length = node.end_lineno - node.lineno + 1
                    
                    if method_length > 50:  # Threshold for long methods
                        opportunities.append(RefactoringOpportunity(
                            location=f"{file_path}:{node.name}:line {node.lineno}",
                            type="extract_method",
                            description=f"Method '{node.name}' is {method_length} lines long",
                            current_code='\n'.join(lines[node.lineno-1:node.end_lineno][:5]) + '...',
                            suggested_code="Extract logical chunks into separate methods",
                            benefits=[
                                "Improved readability",
                                "Better testability",
                                "Reduced complexity"
                            ],
                            effort_estimate="medium"
                        ))
        
        return opportunities
    
    def _detect_large_classes(self, tree: ast.AST, file_path: str, content: str) -> List[RefactoringOpportunity]:
        """Detect classes that are too large"""
        opportunities = []
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                method_count = len([n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))])
                
                if method_count > 20:  # Threshold for large classes
                    opportunities.append(RefactoringOpportunity(
                        location=f"{file_path}:{node.name}:line {node.lineno}",
                        type="extract_class",
                        description=f"Class '{node.name}' has {method_count} methods",
                        current_code=f"class {node.name}:",
                        suggested_code="Split into multiple classes with single responsibilities",
                        benefits=[
                            "Better separation of concerns",
                            "Improved maintainability",
                            "Enhanced testability"
                        ],
                        effort_estimate="high"
                    ))
        
        return opportunities
    
    def _detect_complex_conditions(self, tree: ast.AST, file_path: str, content: str) -> List[RefactoringOpportunity]:
        """Detect complex conditional statements"""
        opportunities = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Count boolean operators in condition
                bool_ops = len([n for n in ast.walk(node.test) if isinstance(n, ast.BoolOp)])
                
                if bool_ops > 3:  # Complex condition threshold
                    opportunities.append(RefactoringOpportunity(
                        location=f"{file_path}:line {node.lineno}",
                        type="simplify_condition",
                        description=f"Complex conditional with {bool_ops} boolean operators",
                        current_code="if complex_condition:",
                        suggested_code="Extract condition logic into meaningful variable names",
                        benefits=[
                            "Improved readability",
                            "Better debugging",
                            "Easier testing"
                        ],
                        effort_estimate="low"
                    ))
        
        return opportunities
    
    def _detect_magic_numbers(self, tree: ast.AST, file_path: str, content: str) -> List[RefactoringOpportunity]:
        """Detect magic numbers that should be constants"""
        opportunities = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                # Skip common acceptable numbers
                if node.value not in [0, 1, -1, 2, 10, 100, 0.0, 1.0]:
                    opportunities.append(RefactoringOpportunity(
                        location=f"{file_path}:line {node.lineno}",
                        type="extract_constant",
                        description=f"Magic number {node.value} detected",
                        current_code=str(node.value),
                        suggested_code=f"MEANINGFUL_CONSTANT = {node.value}",
                        benefits=[
                            "Improved code documentation",
                            "Easier maintenance",
                            "Reduced duplication"
                        ],
                        effort_estimate="low"
                    ))
        
        return opportunities


class AdapterCodeOptimizer:
    """Main adapter framework code optimization orchestrator"""
    
    def __init__(self, target_directories: List[str] = None):
        self.target_directories = target_directories or [
            'ui/adapters',
            'core/adapters',
            'platforms',
            'ui/components'
        ]
        self.analyzer = CodeAnalyzer()
        self.duplication_detector = DuplicationDetector()
        self.refactoring_analyzer = RefactoringAnalyzer()
        
    def run_comprehensive_optimization_analysis(self) -> OptimizationResult:
        """Run comprehensive code optimization analysis"""
        logger.info("Starting comprehensive adapter code optimization analysis")
        
        start_time = time.time()
        
        # Discover Python files
        python_files = self._discover_python_files()
        logger.info(f"Found {len(python_files)} Python files to analyze")
        
        # Analyze files in parallel
        file_analysis_results = self._analyze_files_parallel(python_files)
        
        # Extract file contents for duplication detection
        file_contents = {
            file_path: data['content'] 
            for file_path, data in file_analysis_results.items() 
            if 'content' in data
        }
        
        # Detect code duplications
        logger.info("Detecting code duplications...")
        duplications = self.duplication_detector.detect_duplications(file_contents)
        
        # Analyze refactoring opportunities
        logger.info("Analyzing refactoring opportunities...")
        refactoring_opportunities = self.refactoring_analyzer.analyze_refactoring_opportunities(
            file_analysis_results
        )
        
        # Aggregate metrics and results
        aggregated_metrics = self._aggregate_metrics(file_analysis_results)
        all_bottlenecks = self._aggregate_bottlenecks(file_analysis_results)
        
        # Calculate optimization score
        optimization_score = self._calculate_optimization_score(
            aggregated_metrics, duplications, refactoring_opportunities, all_bottlenecks
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            aggregated_metrics, duplications, refactoring_opportunities, all_bottlenecks
        )
        
        analysis_time = time.time() - start_time
        
        result = OptimizationResult(
            total_files_analyzed=len(python_files),
            code_metrics=aggregated_metrics,
            performance_bottlenecks=all_bottlenecks,
            code_duplications=duplications,
            refactoring_opportunities=refactoring_opportunities,
            optimization_score=optimization_score,
            recommendations=recommendations
        )
        
        logger.info(f"Code optimization analysis completed in {analysis_time:.2f}s")
        logger.info(f"Optimization score: {optimization_score:.1f}/100")
        
        return result
    
    def _discover_python_files(self) -> List[str]:
        """Discover Python files in target directories"""
        python_files = []
        
        for directory in self.target_directories:
            if os.path.exists(directory):
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        if file.endswith('.py') and not file.startswith('__'):
                            python_files.append(os.path.join(root, file))
        
        return python_files
    
    def _analyze_files_parallel(self, python_files: List[str]) -> Dict[str, Any]:
        """Analyze files in parallel for better performance"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_file = {
                executor.submit(self.analyzer.analyze_file, file_path): file_path 
                for file_path in python_files
            }
            
            for future in concurrent.futures.as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    results[file_path] = result
                except Exception as e:
                    logger.error(f"Error analyzing {file_path}: {e}")
                    results[file_path] = {'error': str(e)}
        
        return results
    
    def _aggregate_metrics(self, file_results: Dict[str, Any]) -> CodeMetrics:
        """Aggregate metrics from all analyzed files"""
        aggregated = CodeMetrics()
        
        for file_path, data in file_results.items():
            if 'metrics' in data and isinstance(data['metrics'], CodeMetrics):
                metrics = data['metrics']
                aggregated.lines_of_code += metrics.lines_of_code
                aggregated.cyclomatic_complexity += metrics.cyclomatic_complexity
                aggregated.cognitive_complexity += metrics.cognitive_complexity
                aggregated.class_count += metrics.class_count
                aggregated.function_count += metrics.function_count
                aggregated.comment_ratio += metrics.comment_ratio
        
        # Calculate averages
        file_count = len([d for d in file_results.values() if 'metrics' in d])
        if file_count > 0:
            aggregated.comment_ratio /= file_count
            aggregated.maintainability_index = sum(
                data['metrics'].maintainability_index 
                for data in file_results.values() 
                if 'metrics' in data and isinstance(data['metrics'], CodeMetrics)
            ) / file_count
        
        return aggregated
    
    def _aggregate_bottlenecks(self, file_results: Dict[str, Any]) -> List[PerformanceBottleneck]:
        """Aggregate performance bottlenecks from all files"""
        all_bottlenecks = []
        
        for file_path, data in file_results.items():
            if 'bottlenecks' in data:
                all_bottlenecks.extend(data['bottlenecks'])
        
        # Sort by severity
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        all_bottlenecks.sort(key=lambda x: severity_order.get(x.severity, 4))
        
        return all_bottlenecks
    
    def _calculate_optimization_score(self, metrics: CodeMetrics, 
                                    duplications: List[CodeDuplication],
                                    opportunities: List[RefactoringOpportunity],
                                    bottlenecks: List[PerformanceBottleneck]) -> float:
        """Calculate overall optimization score (0-100)"""
        score = 100.0
        
        # Deduct for complexity
        if metrics.cyclomatic_complexity > metrics.function_count * 5:  # Avg complexity > 5
            score -= 10
        
        if metrics.cognitive_complexity > metrics.function_count * 3:  # Avg cognitive complexity > 3
            score -= 10
        
        # Deduct for low maintainability
        if metrics.maintainability_index < 70:
            score -= 15
        
        # Deduct for code duplication
        if duplications:
            score -= min(20, len(duplications) * 2)
        
        # Deduct for refactoring opportunities
        if opportunities:
            score -= min(15, len(opportunities))
        
        # Deduct for performance bottlenecks
        critical_bottlenecks = [b for b in bottlenecks if b.severity == 'critical']
        high_bottlenecks = [b for b in bottlenecks if b.severity == 'high']
        
        score -= len(critical_bottlenecks) * 10
        score -= len(high_bottlenecks) * 5
        
        # Bonus for good comment ratio
        if metrics.comment_ratio > 0.15:  # > 15% comments
            score += 5
        
        return max(0, min(100, score))
    
    def _generate_recommendations(self, metrics: CodeMetrics,
                                duplications: List[CodeDuplication],
                                opportunities: List[RefactoringOpportunity],
                                bottlenecks: List[PerformanceBottleneck]) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Complexity recommendations
        if metrics.cyclomatic_complexity > metrics.function_count * 5:
            recommendations.append(
                "HIGH PRIORITY: Reduce cyclomatic complexity by breaking down complex functions"
            )
        
        if metrics.cognitive_complexity > metrics.function_count * 3:
            recommendations.append(
                "HIGH PRIORITY: Simplify complex logic and nested structures"
            )
        
        # Maintainability recommendations
        if metrics.maintainability_index < 70:
            recommendations.append(
                "MEDIUM PRIORITY: Improve code maintainability through refactoring and documentation"
            )
        
        # Performance recommendations
        critical_bottlenecks = [b for b in bottlenecks if b.severity in ['critical', 'high']]
        if critical_bottlenecks:
            recommendations.append(
                f"HIGH PRIORITY: Address {len(critical_bottlenecks)} critical performance bottlenecks"
            )
        
        # Duplication recommendations
        if duplications:
            recommendations.append(
                f"MEDIUM PRIORITY: Eliminate {len(duplications)} code duplication instances"
            )
        
        # Refactoring recommendations
        if opportunities:
            high_impact = [o for o in opportunities if o.type in ['extract_method', 'extract_class']]
            if high_impact:
                recommendations.append(
                    f"MEDIUM PRIORITY: Implement {len(high_impact)} high-impact refactoring opportunities"
                )
        
        # Comment recommendations
        if metrics.comment_ratio < 0.1:
            recommendations.append(
                "LOW PRIORITY: Increase code documentation and comments"
            )
        
        # General recommendations
        if not recommendations:
            recommendations.append("Code quality is excellent! Consider minor optimizations for performance.")
        
        return recommendations
    
    def save_optimization_report(self, result: OptimizationResult, filename: str = None) -> str:
        """Save optimization analysis report to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scripts_dev/performance_results/adapter_code_optimization_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Convert dataclasses to dict for JSON serialization
        report_data = {
            'timestamp': result.timestamp.isoformat(),
            'total_files_analyzed': result.total_files_analyzed,
            'optimization_score': result.optimization_score,
            'code_metrics': {
                'lines_of_code': result.code_metrics.lines_of_code,
                'cyclomatic_complexity': result.code_metrics.cyclomatic_complexity,
                'cognitive_complexity': result.code_metrics.cognitive_complexity,
                'maintainability_index': result.code_metrics.maintainability_index,
                'class_count': result.code_metrics.class_count,
                'function_count': result.code_metrics.function_count,
                'comment_ratio': result.code_metrics.comment_ratio
            },
            'performance_bottlenecks': [
                {
                    'location': b.location,
                    'type': b.type,
                    'severity': b.severity,
                    'description': b.description,
                    'suggested_fix': b.suggested_fix,
                    'estimated_improvement': b.estimated_improvement
                } for b in result.performance_bottlenecks
            ],
            'code_duplications': [
                {
                    'file1': d.file1,
                    'file2': d.file2,
                    'line_start_1': d.line_start_1,
                    'line_end_1': d.line_end_1,
                    'line_start_2': d.line_start_2,
                    'line_end_2': d.line_end_2,
                    'similarity_score': d.similarity_score,
                    'duplicate_lines': d.duplicate_lines,
                    'code_snippet': d.code_snippet
                } for d in result.code_duplications
            ],
            'refactoring_opportunities': [
                {
                    'location': o.location,
                    'type': o.type,
                    'description': o.description,
                    'benefits': o.benefits,
                    'effort_estimate': o.effort_estimate
                } for o in result.refactoring_opportunities
            ],
            'recommendations': result.recommendations
        }
        
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"Optimization report saved to: {filename}")
        return filename


def main():
    """Demonstrate adapter code optimization system"""
    print("=== Adapter Framework Code Optimization System ===\n")
    
    # Initialize optimizer
    optimizer = AdapterCodeOptimizer()
    
    # Run comprehensive analysis
    print("Running comprehensive code optimization analysis...")
    result = optimizer.run_comprehensive_optimization_analysis()
    
    # Save report
    report_file = optimizer.save_optimization_report(result)
    
    # Display summary
    print(f"\n{'='*60}")
    print("ADAPTER CODE OPTIMIZATION ANALYSIS SUMMARY")
    print(f"{'='*60}")
    
    print(f"Total Files Analyzed: {result.total_files_analyzed}")
    print(f"Optimization Score: {result.optimization_score:.1f}/100")
    
    print(f"\nCode Metrics:")
    metrics = result.code_metrics
    print(f"  Lines of Code: {metrics.lines_of_code:,}")
    print(f"  Functions: {metrics.function_count}")
    print(f"  Classes: {metrics.class_count}")
    print(f"  Cyclomatic Complexity: {metrics.cyclomatic_complexity}")
    print(f"  Cognitive Complexity: {metrics.cognitive_complexity}")
    print(f"  Maintainability Index: {metrics.maintainability_index:.1f}")
    print(f"  Comment Ratio: {metrics.comment_ratio:.1%}")
    
    print(f"\nIssues Detected:")
    print(f"  Performance Bottlenecks: {len(result.performance_bottlenecks)}")
    print(f"  Code Duplications: {len(result.code_duplications)}")
    print(f"  Refactoring Opportunities: {len(result.refactoring_opportunities)}")
    
    if result.performance_bottlenecks:
        critical_bottlenecks = [b for b in result.performance_bottlenecks if b.severity in ['critical', 'high']]
        print(f"  Critical/High Priority Issues: {len(critical_bottlenecks)}")
    
    print(f"\nTop Recommendations:")
    for i, rec in enumerate(result.recommendations[:5], 1):
        print(f"  {i}. {rec}")
    
    print(f"\nDetailed report saved to: {report_file}")
    
    return result


if __name__ == "__main__":
    main() 