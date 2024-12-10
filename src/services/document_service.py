import pandas as pd
import os
from datetime import datetime
from typing import List, Dict

class DocumentService:
    @staticmethod
    async def save_to_excel(companies: List[Dict]) -> str:
        """Save research data to Excel file."""
        try:
            if not companies:
                print("Warning: No data to export")
                return "reports/no_data.txt"
            
     
            df = pd.DataFrame(companies)
            
            os.makedirs('reports', exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"reports/market_research_{timestamp}.xlsx"
            
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Market Research')
                
                workbook = writer.book
                worksheet = writer.sheets['Market Research']
                
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#4F81BD',
                    'font_color': 'white',
                    'border': 1
                })
                
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
             
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(col)
                    ) + 2
                    worksheet.set_column(idx, idx, min(max_length, 50))
                
            
                worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)
            
            print(f"\nSuccessfully exported {len(companies)} companies to Excel")
            return filename
            
        except Exception as e:
            print(f"Error saving to Excel: {str(e)}")
            error_file = "reports/export_error.txt"
            os.makedirs('reports', exist_ok=True)
            with open(error_file, 'w') as f:
                f.write(f"Error exporting data: {str(e)}")
            return error_file