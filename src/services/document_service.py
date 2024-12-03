import pandas as pd
import os
from datetime import datetime
from ..models.research_models import CompanyInfo
from typing import List

class DocumentService:
    @staticmethod
    async def save_to_excel(companies: List[CompanyInfo]) -> str:
        """Save research data to Excel file."""
        try:
            data = []
            for company in companies:
                if not isinstance(company, CompanyInfo):
                    print(f"Warning: Skipping invalid company data: {company}")
                    continue
                    
                company_dict = company.model_dump()
                
                for product in company_dict['products']:
                    product_data = {
                        'Company Name': company_dict['name'],
                        'Product Name': product,
                        'Price': company_dict['pricing'].get(product, 'Not available'),
                        'Features': '\n'.join(company_dict['product_details']['features'].get(product, [])),
                        'Specifications': '\n'.join(company_dict['product_details']['specifications'].get(product, [])),
                        'Availability': company_dict['product_details']['availability'].get(product, 'Not specified'),
                        'Company Rating': company_dict['rating'],
                        'Total Reviews': company_dict['review_analysis']['total_reviews'],
                        'Average Rating': company_dict['review_analysis']['average_rating'],
                        'Positive Points': '\n'.join(company_dict['review_analysis']['positive_points']),
                        'Negative Points': '\n'.join(company_dict['review_analysis']['negative_points']),
                        'Customer Sentiment': company_dict['review_analysis']['customer_sentiment'],
                        'Market Share': company_dict['market_details']['market_share'],
                        'Target Segment': company_dict['market_details']['target_segment'],
                        'Key Competitors': '\n'.join(company_dict['market_details']['key_competitors']),
                        'Website': company_dict['website'],
                        'Contact': company_dict['contact']
                    }
                    data.append(product_data)
            
            if not data:
                print("Warning: No valid data to export")
                return "reports/no_data.txt"
                
            df = pd.DataFrame(data)
            
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
            
            print(f"\nSuccessfully exported {len(data)} items to Excel")
            return filename
            
        except Exception as e:
            print(f"Error saving to Excel: {str(e)}")
            error_file = "reports/export_error.txt"
            os.makedirs('reports', exist_ok=True)
            with open(error_file, 'w') as f:
                f.write(f"Error exporting data: {str(e)}")
            return error_file