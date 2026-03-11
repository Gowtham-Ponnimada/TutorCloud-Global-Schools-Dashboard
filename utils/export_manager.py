"""
Export Manager for TutorCloud Global Dashboard

Handles data export to Excel and CSV formats with proper formatting.
"""

import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from typing import Optional, List, Dict
import logging


class ExportManager:
    """
    Manages data export operations
    
    Features:
    - Export to Excel (XLSX) with formatting
    - Export to CSV
    - Row limit enforcement (default 50,000)
    - Metadata inclusion (timestamp, filters, etc.)
    """
    
    def __init__(self, max_rows: int = 50000):
        """
        Initialize export manager
        
        Args:
            max_rows: Maximum number of rows to export (default 50,000)
        """
        self.max_rows = max_rows
        self.logger = logging.getLogger(__name__)
    
    def to_excel(
        self,
        df: pd.DataFrame,
        filename: str,
        sheet_name: str = "Data",
        metadata: Optional[Dict[str, str]] = None
    ) -> BytesIO:
        """
        Export DataFrame to Excel with formatting
        
        Args:
            df: DataFrame to export
            filename: Output filename (will add .xlsx extension)
            sheet_name: Name of the Excel sheet
            metadata: Optional metadata to include (filters, timestamp, etc.)
        
        Returns:
            BytesIO object containing Excel file
        """
        # Check row limit
        if len(df) > self.max_rows:
            st.warning(f"⚠️ Data has {len(df):,} rows. Limiting export to {self.max_rows:,} rows.")
            df = df.head(self.max_rows)
        
        # Create Excel file in memory
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Write main data
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Get the worksheet
            worksheet = writer.sheets[sheet_name]
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                adjusted_width = min(max_length + 2, 50)  # Max width 50
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Add metadata sheet if provided
            if metadata:
                metadata_df = pd.DataFrame(
                    list(metadata.items()),
                    columns=['Property', 'Value']
                )
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
        
        output.seek(0)
        return output
    
    def to_csv(
        self,
        df: pd.DataFrame,
        filename: str
    ) -> str:
        """
        Export DataFrame to CSV
        
        Args:
            df: DataFrame to export
            filename: Output filename (will add .csv extension)
        
        Returns:
            CSV string
        """
        # Check row limit
        if len(df) > self.max_rows:
            st.warning(f"⚠️ Data has {len(df):,} rows. Limiting export to {self.max_rows:,} rows.")
            df = df.head(self.max_rows)
        
        return df.to_csv(index=False)
    
    def render_export_buttons(
        self,
        df: pd.DataFrame,
        base_filename: str,
        metadata: Optional[Dict[str, str]] = None,
        sheet_name: str = "Data"
    ) -> None:
        """
        Render export buttons in the UI
        
        Args:
            df: DataFrame to export
            base_filename: Base filename (without extension)
            metadata: Optional metadata dict
            sheet_name: Excel sheet name
        """
        # Add timestamp to filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_with_timestamp = f"{base_filename}_{timestamp}"
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Excel export
            excel_data = self.to_excel(df, filename_with_timestamp, sheet_name, metadata)
            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name=f"{filename_with_timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col2:
            # CSV export
            csv_data = self.to_csv(df, filename_with_timestamp)
            st.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name=f"{filename_with_timestamp}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        # Show row count info
        if len(df) > 0:
            st.caption(f"📊 Exporting {len(df):,} rows")
            if len(df) >= self.max_rows:
                st.caption(f"⚠️ Export limited to {self.max_rows:,} rows. Apply filters to reduce data.")
    
    def create_metadata(
        self,
        filters: Optional[Dict] = None,
        page_name: Optional[str] = None,
        additional_info: Optional[Dict] = None
    ) -> Dict[str, str]:
        """
        Create metadata dictionary for export
        
        Args:
            filters: Applied filters dict
            page_name: Name of the page/report
            additional_info: Any additional information
        
        Returns:
            Metadata dictionary
        """
        metadata = {
            'Export Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Dashboard': 'TutorCloud Global Dashboard'
        }
        
        if page_name:
            metadata['Report'] = page_name
        
        if filters:
            for key, value in filters.items():
                if value:
                    metadata[f'Filter: {key}'] = str(value)
        
        if additional_info:
            metadata.update(additional_info)
        
        return metadata


# Global export manager instance
export_manager = ExportManager(max_rows=50000)
