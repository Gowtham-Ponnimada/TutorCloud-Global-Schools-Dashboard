"""
Cache Manager for TutorCloud Global Dashboard

Provides query result caching with TTL (Time To Live) support.
Uses Streamlit's session state for caching within user sessions.
"""

import streamlit as st
import hashlib
import json
import time
from typing import Any, Optional, Dict
from datetime import datetime, timedelta


class CacheManager:
    """
    Manages query result caching with TTL support
    
    Features:
    - Session-based caching (per user)
    - Configurable TTL (default 300 seconds)
    - Cache invalidation by pattern
    - Cache statistics
    """
    
    def __init__(self):
        """Initialize cache in Streamlit session state"""
        if 'query_cache' not in st.session_state:
            st.session_state.query_cache = {}
        if 'cache_stats' not in st.session_state:
            st.session_state.cache_stats = {
                'hits': 0,
                'misses': 0,
                'sets': 0,
                'invalidations': 0
            }
    
    def _generate_key(self, query: str, params: Optional[tuple] = None) -> str:
        """
        Generate cache key from query and parameters
        
        Args:
            query: SQL query string
            params: Query parameters tuple
            
        Returns:
            Hash string as cache key
        """
        cache_input = query
        if params:
            cache_input += str(params)
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    def get(self, query: str, params: Optional[tuple] = None, ttl: int = 300) -> Optional[Any]:
        """
        Get cached result if available and not expired
        
        Args:
            query: SQL query string
            params: Query parameters
            ttl: Time to live in seconds (default 300 = 5 minutes)
            
        Returns:
            Cached result or None if not found/expired
        """
        key = self._generate_key(query, params)
        
        if key in st.session_state.query_cache:
            cache_entry = st.session_state.query_cache[key]
            
            # Check if expired
            if time.time() - cache_entry['timestamp'] < ttl:
                st.session_state.cache_stats['hits'] += 1
                return cache_entry['data']
            else:
                # Expired, remove from cache
                del st.session_state.query_cache[key]
        
        st.session_state.cache_stats['misses'] += 1
        return None
    
    def set(self, query: str, data: Any, params: Optional[tuple] = None) -> None:
        """
        Store result in cache
        
        Args:
            query: SQL query string
            data: Data to cache (DataFrame, list, dict, etc.)
            params: Query parameters
        """
        key = self._generate_key(query, params)
        
        st.session_state.query_cache[key] = {
            'data': data,
            'timestamp': time.time(),
            'query': query[:100]  # Store first 100 chars for debugging
        }
        
        st.session_state.cache_stats['sets'] += 1
    
    def invalidate(self, pattern: Optional[str] = None) -> int:
        """
        Invalidate cache entries matching pattern
        
        Args:
            pattern: Pattern to match in query (case-insensitive)
                    If None, clears entire cache
        
        Returns:
            Number of entries invalidated
        """
        if pattern is None:
            # Clear entire cache
            count = len(st.session_state.query_cache)
            st.session_state.query_cache = {}
            st.session_state.cache_stats['invalidations'] += count
            return count
        
        # Invalidate matching entries
        keys_to_delete = []
        pattern_lower = pattern.lower()
        
        for key, entry in st.session_state.query_cache.items():
            if pattern_lower in entry['query'].lower():
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del st.session_state.query_cache[key]
        
        st.session_state.cache_stats['invalidations'] += len(keys_to_delete)
        return len(keys_to_delete)
    
    def invalidate_by_table(self, table_name: str) -> int:
        """
        Invalidate all queries involving a specific table
        
        Args:
            table_name: Name of table to invalidate
            
        Returns:
            Number of entries invalidated
        """
        return self.invalidate(f"FROM {table_name}")
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with hits, misses, sets, invalidations
        """
        stats = st.session_state.cache_stats.copy()
        stats['current_size'] = len(st.session_state.query_cache)
        
        # Calculate hit rate
        total_requests = stats['hits'] + stats['misses']
        stats['hit_rate'] = (stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return stats
    
    def clear_all(self) -> None:
        """Clear entire cache and reset statistics"""
        st.session_state.query_cache = {}
        st.session_state.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'invalidations': 0
        }
    
    def get_cache_size(self) -> int:
        """Get number of cached entries"""
        return len(st.session_state.query_cache)
    
    def cleanup_expired(self, ttl: int = 300) -> int:
        """
        Remove expired cache entries
        
        Args:
            ttl: Time to live in seconds
            
        Returns:
            Number of entries removed
        """
        current_time = time.time()
        keys_to_delete = []
        
        for key, entry in st.session_state.query_cache.items():
            if current_time - entry['timestamp'] >= ttl:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del st.session_state.query_cache[key]
        
        return len(keys_to_delete)


# Global cache instance
cache_manager = CacheManager()
