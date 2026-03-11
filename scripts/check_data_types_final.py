"""
Check actual data types in the database using existing DB connection
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.utils.database import DatabaseManager
from src.config.settings import settings

def check_data_types():
    db = DatabaseManager(settings)
    
    print("=" * 80)
    print("DATA TYPE VERIFICATION - CRITICAL COLUMNS")
    print("=" * 80)
    
    # Check school_profile_1 critical columns
    print("\n=== SCHOOL_PROFILE_1 DATA TYPES ===\n")
    query = """
        SELECT 
            column_name,
            data_type,
            CASE 
                WHEN data_type IN ('integer', 'bigint', 'numeric', 'decimal', 'double precision', 'smallint') THEN '✅ Numeric'
                WHEN data_type = 'character varying' THEN '❌ VARCHAR'
                ELSE '⚠️ ' || data_type
            END as status
        FROM information_schema.columns
        WHERE table_schema = 'india_2024_25'
        AND table_name = 'school_profile_1'
        AND column_name IN ('managment', 'pincode', 'rural_urban', 'aff_board_sec', 'aff_board_hsec', 'medium_instr1', 'school_category', 'school_type')
        ORDER BY column_name;
    """
    
    result = db.execute_query(query)
    if result:
        print(f"{'Column Name':<20} {'Data Type':<25} {'Status':<15}")
        print("-" * 60)
        for row in result:
            print(f"{row[0]:<20} {row[1]:<25} {row[2]:<15}")
    
    # Check enrollment columns
    print("\n=== ENROLLMENT_DETAIL_1 DATA TYPES ===\n")
    query = """
        SELECT 
            column_name,
            data_type,
            CASE 
                WHEN data_type IN ('integer', 'bigint', 'numeric', 'decimal', 'smallint') THEN '✅ Numeric'
                WHEN data_type = 'character varying' THEN '❌ VARCHAR'
                ELSE '⚠️ ' || data_type
            END as status
        FROM information_schema.columns
        WHERE table_schema = 'india_2024_25'
        AND table_name = 'enrollment_detail_1'
        AND column_name IN ('c1_b', 'c1_g', 'c2_b', 'c2_g', 'cpp_b', 'cpp_g', 'c3_b', 'c3_g', 'c4_b', 'c4_g')
        ORDER BY column_name;
    """
    
    result = db.execute_query(query)
    if result:
        print(f"{'Column Name':<20} {'Data Type':<25} {'Status':<15}")
        print("-" * 60)
        for row in result:
            print(f"{row[0]:<20} {row[1]:<25} {row[2]:<15}")
    
    # Check teacher columns
    print("\n=== TEACHER_DATA DATA TYPES ===\n")
    query = """
        SELECT 
            column_name,
            data_type,
            CASE 
                WHEN data_type IN ('integer', 'bigint', 'numeric', 'decimal', 'smallint') THEN '✅ Numeric'
                WHEN data_type = 'character varying' THEN '❌ VARCHAR'
                ELSE '⚠️ ' || data_type
            END as status
        FROM information_schema.columns
        WHERE table_schema = 'india_2024_25'
        AND table_name = 'teacher_data'
        AND column_name IN ('total_tch', 'male_tch', 'female_tch')
        ORDER BY column_name;
    """
    
    result = db.execute_query(query)
    if result:
        print(f"{'Column Name':<20} {'Data Type':<25} {'Status':<15}")
        print("-" * 60)
        for row in result:
            print(f"{row[0]:<20} {row[1]:<25} {row[2]:<15}")
    
    # Get ALL columns from school_profile_1
    print("\n=== ALL SCHOOL_PROFILE_1 COLUMNS ===\n")
    query = """
        SELECT 
            column_name,
            data_type,
            character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = 'india_2024_25'
        AND table_name = 'school_profile_1'
        ORDER BY ordinal_position;
    """
    
    result = db.execute_query(query)
    if result:
        print(f"{'Column Name':<30} {'Data Type':<25} {'Max Length':<15}")
        print("-" * 70)
        for row in result:
            max_len = str(row[2]) if row[2] else 'N/A'
            print(f"{row[0]:<30} {row[1]:<25} {max_len:<15}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 80)
    
    # Count VARCHAR vs Numeric in critical columns
    query = """
        SELECT 
            CASE 
                WHEN data_type IN ('integer', 'bigint', 'numeric', 'decimal', 'smallint') THEN 'Numeric (Good)'
                WHEN data_type = 'character varying' THEN 'VARCHAR (Need Fix)'
                ELSE 'Other'
            END as type_category,
            COUNT(*) as column_count
        FROM information_schema.columns
        WHERE table_schema = 'india_2024_25'
        AND table_name = 'school_profile_1'
        AND column_name IN (
            'managment', 'pincode', 'rural_urban', 
            'aff_board_sec', 'aff_board_hsec', 'medium_instr1',
            'school_category', 'school_type'
        )
        GROUP BY type_category;
    """
    
    result = db.execute_query(query)
    varchar_count = 0
    numeric_count = 0
    if result:
        print("\nCritical Columns Status:")
        for row in result:
            print(f"  {row[0]}: {row[1]} columns")
            if 'VARCHAR' in row[0]:
                varchar_count = row[1]
            elif 'Numeric' in row[0]:
                numeric_count = row[1]
    
    # Recommendation
    print("\n" + "=" * 80)
    if varchar_count > 0:
        print("⚠️  ACTION REQUIRED: VARCHAR columns found in critical fields")
        print("=" * 80)
        print("\nNext steps:")
        print("1. We need to convert VARCHAR columns to INTEGER")
        print("2. This will take 15-30 minutes")
        print("3. Dashboard build will proceed after conversion")
    else:
        print("✅ ALL CRITICAL COLUMNS ARE PROPERLY TYPED!")
        print("=" * 80)
        print("\nNext steps:")
        print("1. ✅ Data types verified - all numeric columns are correct")
        print("2. ✅ Ready to proceed with Phase 3 dashboard build")
        print("3. 🚀 No schema changes needed - we can start building now!")
    
    db.close()
    
    print("\n" + "=" * 80)
    print("✅ DATA TYPE CHECK COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    check_data_types()
