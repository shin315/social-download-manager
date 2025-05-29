"""
Advanced Query Builder and Methods for Social Download Manager v2.0

Enhanced query building capabilities with support for complex queries,
aggregations, and specialized data analysis operations.
"""

from typing import List, Dict, Any, Optional, Union, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

from .base import EntityId
from .repositories import QueryBuilder, RepositoryError


class SortDirection(Enum):
    """Sort direction enumeration"""
    ASC = "ASC"
    DESC = "DESC"


class AggregateFunction(Enum):
    """Aggregate function enumeration"""
    COUNT = "COUNT"
    SUM = "SUM"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"
    GROUP_CONCAT = "GROUP_CONCAT"


class DateRange:
    """Date range helper for time-based queries"""
    
    def __init__(self, start: Optional[datetime] = None, end: Optional[datetime] = None):
        self.start = start
        self.end = end
    
    @classmethod
    def last_days(cls, days: int) -> 'DateRange':
        """Create range for last N days"""
        end = datetime.now()
        start = end - timedelta(days=days)
        return cls(start, end)
    
    @classmethod
    def last_hours(cls, hours: int) -> 'DateRange':
        """Create range for last N hours"""
        end = datetime.now()
        start = end - timedelta(hours=hours)
        return cls(start, end)
    
    @classmethod
    def today(cls) -> 'DateRange':
        """Create range for today"""
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return cls(start, end)
    
    def to_iso_strings(self) -> Tuple[Optional[str], Optional[str]]:
        """Convert to ISO format strings"""
        start_iso = self.start.isoformat() if self.start else None
        end_iso = self.end.isoformat() if self.end else None
        return start_iso, end_iso


class AdvancedQueryBuilder(QueryBuilder):
    """
    Enhanced query builder with support for complex operations
    
    Extends base QueryBuilder with aggregations, joins, subqueries,
    and specialized query patterns for analytics.
    """
    
    def __init__(self, table_name: str):
        super().__init__(table_name)
        self.group_by_fields = []
        self.having_conditions = []
        self.having_values = []
        self.aggregate_fields = []
        self.distinct = False
        self.subqueries = []
    
    def select_distinct(self, fields: Union[str, List[str]]) -> 'AdvancedQueryBuilder':
        """Set SELECT DISTINCT fields"""
        self.distinct = True
        return self.select(fields)
    
    def select_aggregate(self, func: AggregateFunction, field: str, alias: str = None) -> 'AdvancedQueryBuilder':
        """Add aggregate function to SELECT"""
        if alias:
            aggregate = f"{func.value}({field}) AS {alias}"
        else:
            aggregate = f"{func.value}({field})"
        
        self.aggregate_fields.append(aggregate)
        return self
    
    def select_count(self, field: str = "*", alias: str = "count") -> 'AdvancedQueryBuilder':
        """Add COUNT to SELECT"""
        return self.select_aggregate(AggregateFunction.COUNT, field, alias)
    
    def select_sum(self, field: str, alias: str = None) -> 'AdvancedQueryBuilder':
        """Add SUM to SELECT"""
        return self.select_aggregate(AggregateFunction.SUM, field, alias or f"{field}_sum")
    
    def select_avg(self, field: str, alias: str = None) -> 'AdvancedQueryBuilder':
        """Add AVG to SELECT"""
        return self.select_aggregate(AggregateFunction.AVG, field, alias or f"{field}_avg")
    
    def where_null(self, field: str) -> 'AdvancedQueryBuilder':
        """Add WHERE field IS NULL condition"""
        self.where_conditions.append(f"{field} IS NULL")
        return self
    
    def where_not_null(self, field: str) -> 'AdvancedQueryBuilder':
        """Add WHERE field IS NOT NULL condition"""
        self.where_conditions.append(f"{field} IS NOT NULL")
        return self
    
    def where_greater_than(self, field: str, value: Any) -> 'AdvancedQueryBuilder':
        """Add WHERE field > value condition"""
        self.where_conditions.append(f"{field} > ?")
        self.where_values.append(value)
        return self
    
    def where_less_than(self, field: str, value: Any) -> 'AdvancedQueryBuilder':
        """Add WHERE field < value condition"""
        self.where_conditions.append(f"{field} < ?")
        self.where_values.append(value)
        return self
    
    def where_date_range(self, field: str, date_range: DateRange) -> 'AdvancedQueryBuilder':
        """Add WHERE field in date range condition"""
        start_iso, end_iso = date_range.to_iso_strings()
        
        if start_iso and end_iso:
            self.where_between(field, start_iso, end_iso)
        elif start_iso:
            self.where_greater_than(field, start_iso)
        elif end_iso:
            self.where_less_than(field, end_iso)
        
        return self
    
    def where_or(self, conditions: List[str], values: List[Any]) -> 'AdvancedQueryBuilder':
        """Add WHERE (condition1 OR condition2 OR ...) condition"""
        if conditions:
            or_condition = f"({' OR '.join(conditions)})"
            self.where_conditions.append(or_condition)
            self.where_values.extend(values)
        return self
    
    def group_by(self, *fields: str) -> 'AdvancedQueryBuilder':
        """Add GROUP BY fields"""
        self.group_by_fields.extend(fields)
        return self
    
    def having(self, condition: str, *values: Any) -> 'AdvancedQueryBuilder':
        """Add HAVING condition"""
        self.having_conditions.append(condition)
        self.having_values.extend(values)
        return self
    
    def having_count_greater_than(self, count: int) -> 'AdvancedQueryBuilder':
        """Add HAVING COUNT(*) > count condition"""
        return self.having("COUNT(*) > ?", count)
    
    def inner_join(self, table: str, on_condition: str) -> 'AdvancedQueryBuilder':
        """Add INNER JOIN"""
        self.join_clauses.append(f"INNER JOIN {table} ON {on_condition}")
        return self
    
    def left_join(self, table: str, on_condition: str) -> 'AdvancedQueryBuilder':
        """Add LEFT JOIN"""
        self.join_clauses.append(f"LEFT JOIN {table} ON {on_condition}")
        return self
    
    def build(self) -> Tuple[str, List[Any]]:
        """Build the final SQL query and parameters"""
        # Build SELECT with aggregates
        select_parts = []
        
        if self.aggregate_fields:
            select_parts.extend(self.aggregate_fields)
        
        if self.select_fields != ["*"] or not self.aggregate_fields:
            select_parts.extend(self.select_fields)
        
        if not select_parts:
            select_parts = ["*"]
        
        # Handle DISTINCT
        distinct_keyword = "DISTINCT " if self.distinct else ""
        select_clause = f"SELECT {distinct_keyword}{', '.join(select_parts)}"
        
        # Build FROM
        from_clause = f"FROM {self.table_name}"
        
        # Build WHERE
        where_clause = ""
        if self.where_conditions:
            where_clause = f"WHERE {' AND '.join(self.where_conditions)}"
        
        # Build GROUP BY
        group_by_clause = ""
        if self.group_by_fields:
            group_by_clause = f"GROUP BY {', '.join(self.group_by_fields)}"
        
        # Build HAVING
        having_clause = ""
        if self.having_conditions:
            having_clause = f"HAVING {' AND '.join(self.having_conditions)}"
        
        # Combine all clauses
        query_parts = [select_clause, from_clause]
        query_parts.extend(self.join_clauses)
        if where_clause:
            query_parts.append(where_clause)
        if group_by_clause:
            query_parts.append(group_by_clause)
        if having_clause:
            query_parts.append(having_clause)
        if self.order_by_clause:
            query_parts.append(self.order_by_clause)
        if self.limit_clause:
            query_parts.append(self.limit_clause)
        
        query = " ".join(query_parts)
        all_values = self.where_values + self.having_values
        return query, all_values


class QueryMethodsMixin:
    """
    Mixin providing advanced query methods for repository implementations
    
    Provides reusable query patterns for common data analysis operations.
    """
    
    def advanced_query(self) -> AdvancedQueryBuilder:
        """Get advanced query builder"""
        return AdvancedQueryBuilder(self._model.get_table_name())
    
    def find_with_pagination(self, page: int = 1, page_size: int = 20, 
                           order_by: str = "created_at", 
                           order_direction: SortDirection = SortDirection.DESC) -> Dict[str, Any]:
        """Find entities with pagination"""
        try:
            # Calculate offset
            offset = (page - 1) * page_size
            
            # Get total count
            total_count = self.count()
            
            # Get paginated results
            query, params = (self.advanced_query()
                           .where_not_deleted()
                           .order_by(order_by, order_direction.value)
                           .limit(page_size, offset)
                           .build())
            
            items = self.execute_query(query, params)
            
            # Calculate pagination info
            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_prev = page > 1
            
            return {
                'items': items,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': has_next,
                    'has_prev': has_prev
                }
            }
            
        except Exception as e:
            self._logger.error(f"Failed to find with pagination: {e}")
            raise RepositoryError(f"Pagination query failed: {e}")
    
    def find_by_date_range(self, date_field: str, date_range: DateRange) -> List:
        """Find entities within date range"""
        try:
            query, params = (self.advanced_query()
                           .where_not_deleted()
                           .where_date_range(date_field, date_range)
                           .order_by(date_field, SortDirection.DESC.value)
                           .build())
            
            return self.execute_query(query, params)
            
        except Exception as e:
            self._logger.error(f"Failed to find by date range: {e}")
            raise RepositoryError(f"Date range query failed: {e}")
    
    def count_by_field(self, field: str) -> Dict[str, int]:
        """Count entities grouped by field value"""
        try:
            query, params = (self.advanced_query()
                           .select([field])
                           .select_count("*", "count")
                           .where_not_deleted()
                           .group_by(field)
                           .order_by("count", SortDirection.DESC.value)
                           .build())
            
            connection = self._model._get_connection()
            try:
                cursor = connection.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                cursor.close()
                
                # Convert to dictionary
                result = {}
                for row in rows:
                    field_value = row[0] if row[0] is not None else "null"
                    count = row[1]
                    result[str(field_value)] = count
                
                return result
                
            finally:
                self._model._return_connection(connection)
                
        except Exception as e:
            self._logger.error(f"Failed to count by field: {e}")
            raise RepositoryError(f"Count by field query failed: {e}")
    
    def find_trends(self, date_field: str, days: int = 30, 
                   group_by_hours: bool = False) -> List[Dict[str, Any]]:
        """Find trends over time period"""
        try:
            date_range = DateRange.last_days(days)
            
            # Group by date or hour
            if group_by_hours:
                date_format = "strftime('%Y-%m-%d %H:00:00', {})".format(date_field)
            else:
                date_format = "strftime('%Y-%m-%d', {})".format(date_field)
            
            # Build query with date grouping
            query = f"""
                SELECT {date_format} as period, COUNT(*) as count
                FROM {self._model.get_table_name()}
                WHERE is_deleted = 0
                AND {date_field} >= ? AND {date_field} <= ?
                GROUP BY {date_format}
                ORDER BY period ASC
            """
            
            start_iso, end_iso = date_range.to_iso_strings()
            params = [start_iso, end_iso]
            
            connection = self._model._get_connection()
            try:
                cursor = connection.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                cursor.close()
                
                # Convert to list of dictionaries
                result = []
                for row in rows:
                    result.append({
                        'period': row[0],
                        'count': row[1]
                    })
                
                return result
                
            finally:
                self._model._return_connection(connection)
                
        except Exception as e:
            self._logger.error(f"Failed to find trends: {e}")
            raise RepositoryError(f"Trends query failed: {e}")
    
    def find_duplicates(self, fields: List[str]) -> List[Dict[str, Any]]:
        """Find duplicate records based on specified fields"""
        try:
            # Build GROUP BY clause
            group_fields = ', '.join(fields)
            
            query = f"""
                SELECT {group_fields}, COUNT(*) as count
                FROM {self._model.get_table_name()}
                WHERE is_deleted = 0
                GROUP BY {group_fields}
                HAVING COUNT(*) > 1
                ORDER BY count DESC
            """
            
            connection = self._model._get_connection()
            try:
                cursor = connection.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                cursor.close()
                
                # Convert to list of dictionaries
                result = []
                for row in rows:
                    duplicate_info = {}
                    for i, field in enumerate(fields):
                        duplicate_info[field] = row[i]
                    duplicate_info['count'] = row[-1]
                    result.append(duplicate_info)
                
                return result
                
            finally:
                self._model._return_connection(connection)
                
        except Exception as e:
            self._logger.error(f"Failed to find duplicates: {e}")
            raise RepositoryError(f"Duplicates query failed: {e}")
    
    def get_field_statistics(self, field: str) -> Dict[str, Any]:
        """Get statistical information about a numeric field"""
        try:
            query = f"""
                SELECT 
                    COUNT({field}) as count,
                    MIN({field}) as min_value,
                    MAX({field}) as max_value,
                    AVG({field}) as avg_value,
                    SUM({field}) as sum_value
                FROM {self._model.get_table_name()}
                WHERE is_deleted = 0 AND {field} IS NOT NULL
            """
            
            connection = self._model._get_connection()
            try:
                cursor = connection.cursor()
                cursor.execute(query)
                row = cursor.fetchone()
                cursor.close()
                
                if row:
                    return {
                        'count': row[0],
                        'min': row[1],
                        'max': row[2],
                        'average': row[3],
                        'sum': row[4]
                    }
                else:
                    return {
                        'count': 0,
                        'min': None,
                        'max': None,
                        'average': None,
                        'sum': None
                    }
                
            finally:
                self._model._return_connection(connection)
                
        except Exception as e:
            self._logger.error(f"Failed to get field statistics: {e}")
            raise RepositoryError(f"Field statistics query failed: {e}")


class QueryOptimizer:
    """
    Query optimization utilities for improving performance
    
    Provides query analysis and optimization recommendations.
    """
    
    @staticmethod
    def explain_query(connection, query: str, params: List[Any] = None) -> Dict[str, Any]:
        """Get query execution plan"""
        try:
            if params is None:
                params = []
            
            cursor = connection.cursor()
            
            # Get query plan
            explain_query = f"EXPLAIN QUERY PLAN {query}"
            cursor.execute(explain_query, params)
            plan_rows = cursor.fetchall()
            
            cursor.close()
            
            return {
                'query': query,
                'parameters': params,
                'execution_plan': [
                    {
                        'selectid': row[0],
                        'order': row[1],
                        'from': row[2],
                        'detail': row[3]
                    } for row in plan_rows
                ]
            }
            
        except Exception as e:
            logging.error(f"Failed to explain query: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def suggest_indexes(table_name: str, frequent_where_fields: List[str]) -> List[str]:
        """Suggest index creation for frequently queried fields"""
        suggestions = []
        
        for field in frequent_where_fields:
            index_name = f"idx_{table_name}_{field}"
            index_sql = f"CREATE INDEX {index_name} ON {table_name} ({field})"
            suggestions.append(index_sql)
        
        # Suggest composite index for common field combinations
        if len(frequent_where_fields) > 1:
            composite_fields = ', '.join(frequent_where_fields[:3])  # Max 3 fields
            composite_index_name = f"idx_{table_name}_composite"
            composite_index_sql = f"CREATE INDEX {composite_index_name} ON {table_name} ({composite_fields})"
            suggestions.append(composite_index_sql)
        
        return suggestions 