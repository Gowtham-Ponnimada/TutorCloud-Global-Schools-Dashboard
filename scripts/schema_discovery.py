#!/usr/bin/env python3
"""
Complete Schema Discovery Script
TutorCloud Global Education Dashboard

This script will document:
1. All tables and their columns with data types
2. Sample data from each table
3. Materialized views structure
4. Actual column names in enrollment tables
5. Relationships and foreign keys
6. Data distributions for key columns
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import settings
from src.utils.database import DatabaseManager
import pandas as pd
import json

class SchemaDiscovery:
    """Comprehensive schema discovery"""
    
    def __init__(self):
        self.db = DatabaseManager(settings)
        self.schema = settings.DB_SCHEMA
        self.results = {
            "tables": {},
            "materialized_views": {},
            "summary": {}
        }
    
    def discover_all(self):
        """Run complete schema discovery"""
        print("="*80)
        print("TUTORCLOUD DATABASE SCHEMA DISCOVERY")
        print("="*80)
        print(f"Database: {settings.DB_NAME}")
        print(f"Schema: {self.schema}")
        print("="*80)
        
        # 1. Discover all tables
        print("\n1. DISCOVERING TABLES...")
        self.discover_tables()
        
        # 2. Discover all columns for each table
        print("\n2. DISCOVERING COLUMNS...")
        self.discover_columns()
        
        # 3. Get sample data
        print("\n3. GETTING SAMPLE DATA...")
        self.get_sample_data()
        
        # 4. Discover materialized views
        print("\n4. DISCOVERING MATERIALIZED VIEWS...")
        self.discover_materialized_views()
        
        # 5. Analyze key columns
        print("\n5. ANALYZING KEY COLUMNS...")
        self.analyze_key_columns()
        
        # 6. Save results
        print("\n6. SAVING RESULTS...")
        self.save_results()
        
        # 7. Print summary
        print("\n7. SUMMARY")
        self.print_summary()
    
    def discover_tables(self):
        """Discover all tables in schema"""
        query = """
            SELECT 
                table_name,
                pg_size_pretty(pg_total_relation_size(quote_ident(table_schema) || '.' || quote_ident(table_name))) as size
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """
        
        with self.db.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=[self.schema])
        
        print(f"\nFound {len(df)} tables:")
        for _, row in df.iterrows():
            table_name = row['table_name']
            size = row['size']
            print(f"  - {table_name} ({size})")
            self.results["tables"][table_name] = {
                "size": size,
                "columns": {},
                "sample_data": []
            }
    
    def discover_columns(self):
        """Discover all columns for each table"""
        for table_name in self.results["tables"].keys():
            query = """
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = %s
                ORDER BY ordinal_position;
            """
            
            with self.db.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=[self.schema, table_name])
            
            print(f"\n{table_name}: {len(df)} columns")
            
            columns = {}
            for _, row in df.iterrows():
                col_name = row['column_name']
                data_type = row['data_type']
                nullable = row['is_nullable']
                
                # Format data type
                if row['character_maximum_length']:
                    data_type = f"{data_type}({row['character_maximum_length']})"
                
                columns[col_name] = {
                    "type": data_type,
                    "nullable": nullable == 'YES',
                    "default": row['column_default']
                }
                
                print(f"  {col_name:30s} {data_type:20s} {'NULL' if nullable == 'YES' else 'NOT NULL'}")
            
            self.results["tables"][table_name]["columns"] = columns
    
    def get_sample_data(self):
        """Get sample data from each table"""
        for table_name in self.results["tables"].keys():
            query = f"""
                SELECT *
                FROM {self.schema}.{table_name}
                LIMIT 3;
            """
            
            try:
                with self.db.get_connection() as conn:
                    df = pd.read_sql_query(query, conn)
                
                # Convert to dict for JSON serialization
                sample_data = df.to_dict('records')
                self.results["tables"][table_name]["sample_data"] = sample_data
                
                print(f"\n{table_name}: Got {len(df)} sample rows")
                
            except Exception as e:
                print(f"\n{table_name}: Error getting sample data - {str(e)}")
    
    def discover_materialized_views(self):
        """Discover all materialized views"""
        query = """
            SELECT 
                matviewname as view_name,
                pg_size_pretty(pg_total_relation_size(schemaname || '.' || matviewname)) as size
            FROM pg_matviews
            WHERE schemaname = %s
            ORDER BY matviewname;
        """
        
        with self.db.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=[self.schema])
        
        print(f"\nFound {len(df)} materialized views:")
        for _, row in df.iterrows():
            view_name = row['view_name']
            size = row['size']
            print(f"  - {view_name} ({size})")
            
            # Get columns
            col_query = """
                SELECT 
                    column_name,
                    data_type
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = %s
                ORDER BY ordinal_position;
            """
            
            with self.db.get_connection() as conn:
                col_df = pd.read_sql_query(col_query, conn, params=[self.schema, view_name])
            
            columns = {}
            for _, col_row in col_df.iterrows():
                columns[col_row['column_name']] = col_row['data_type']
                print(f"    - {col_row['column_name']:30s} {col_row['data_type']}")
            
            self.results["materialized_views"][view_name] = {
                "size": size,
                "columns": columns
            }
    
    def analyze_key_columns(self):
        """Analyze key columns for filters"""
        analyses = []
        
        # 1. States
        print("\n--- STATE DISTRIBUTION ---")
        query = f"""
            SELECT state, COUNT(*) as count
            FROM {self.schema}.school_profile_1
            WHERE state IS NOT NULL
            GROUP BY state
            ORDER BY count DESC
            LIMIT 10;
        """
        with self.db.get_connection() as conn:
            df = pd.read_sql_query(query, conn)
        print(df.to_string(index=False))
        analyses.append({"column": "state", "data": df.to_dict('records')})
        
        # 2. Rural/Urban
        print("\n--- RURAL/URBAN DISTRIBUTION ---")
        query = f"""
            SELECT rural_urban, COUNT(*) as count
            FROM {self.schema}.school_profile_1
            GROUP BY rural_urban
            ORDER BY rural_urban;
        """
        with self.db.get_connection() as conn:
            df = pd.read_sql_query(query, conn)
        print(df.to_string(index=False))
        analyses.append({"column": "rural_urban", "data": df.to_dict('records')})
        
        # 3. Management (note the typo in actual column name)
        print("\n--- MANAGEMENT DISTRIBUTION ---")
        query = f"""
            SELECT managment, COUNT(*) as count
            FROM {self.schema}.school_profile_1
            GROUP BY managment
            ORDER BY managment;
        """
        with self.db.get_connection() as conn:
            df = pd.read_sql_query(query, conn)
        print(df.to_string(index=False))
        analyses.append({"column": "managment", "data": df.to_dict('records')})
        
        # 4. School Category
        print("\n--- SCHOOL CATEGORY DISTRIBUTION ---")
        query = f"""
            SELECT school_category, COUNT(*) as count
            FROM {self.schema}.school_profile_1
            GROUP BY school_category
            ORDER BY school_category;
        """
        with self.db.get_connection() as conn:
            df = pd.read_sql_query(query, conn)
        print(df.to_string(index=False))
        analyses.append({"column": "school_category", "data": df.to_dict('records')})
        
        # 5. School Type
        print("\n--- SCHOOL TYPE DISTRIBUTION ---")
        query = f"""
            SELECT school_type, COUNT(*) as count
            FROM {self.schema}.school_profile_1
            GROUP BY school_type
            ORDER BY school_type;
        """
        with self.db.get_connection() as conn:
            df = pd.read_sql_query(query, conn)
        print(df.to_string(index=False))
        analyses.append({"column": "school_type", "data": df.to_dict('records')})
        
        # 6. Board Affiliation
        print("\n--- BOARD AFFILIATION (SECONDARY) ---")
        query = f"""
            SELECT aff_board_sec, COUNT(*) as count
            FROM {self.schema}.school_profile_1
            GROUP BY aff_board_sec
            ORDER BY count DESC
            LIMIT 10;
        """
        with self.db.get_connection() as conn:
            df = pd.read_sql_query(query, conn)
        print(df.to_string(index=False))
        analyses.append({"column": "aff_board_sec", "data": df.to_dict('records')})
        
        # 7. Medium of Instruction
        print("\n--- MEDIUM OF INSTRUCTION (PRIMARY) ---")
        query = f"""
            SELECT medium_instr1, COUNT(*) as count
            FROM {self.schema}.school_profile_1
            GROUP BY medium_instr1
            ORDER BY count DESC
            LIMIT 10;
        """
        with self.db.get_connection() as conn:
            df = pd.read_sql_query(query, conn)
        print(df.to_string(index=False))
        analyses.append({"column": "medium_instr1", "data": df.to_dict('records')})
        
        self.results["key_column_analysis"] = analyses
    
    def save_results(self):
        """Save results to JSON file"""
        output_file = "/mnt/user-data/outputs/schema_discovery_results.json"
        
        # Convert to JSON-serializable format
        json_results = json.dumps(self.results, indent=2, default=str)
        
        with open(output_file, 'w') as f:
            f.write(json_results)
        
        print(f"\nResults saved to: {output_file}")
    
    def print_summary(self):
        """Print summary of discovery"""
        print("\n" + "="*80)
        print("DISCOVERY SUMMARY")
        print("="*80)
        
        print(f"\nTables: {len(self.results['tables'])}")
        for table_name, table_info in self.results["tables"].items():
            col_count = len(table_info["columns"])
            print(f"  - {table_name:30s} {col_count:3d} columns  {table_info['size']}")
        
        print(f"\nMaterialized Views: {len(self.results['materialized_views'])}")
        for view_name, view_info in self.results["materialized_views"].items():
            col_count = len(view_info["columns"])
            print(f"  - {view_name:30s} {col_count:3d} columns  {view_info['size']}")
        
        print("\n" + "="*80)


if __name__ == "__main__":
    discovery = SchemaDiscovery()
    discovery.discover_all()
    
    print("\n✅ SCHEMA DISCOVERY COMPLETE!")
    print("\nNext steps:")
    print("1. Review the output above")
    print("2. Check schema_discovery_results.json")
    print("3. I'll rebuild Phase 2 with correct schema")
