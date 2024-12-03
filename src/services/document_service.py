import pandas as pd
import os
from datetime import datetime

class DocumentService:
    @staticmethod
    async def save_to_excel(companies: list) -> str:
        """Save company data to Excel file."""
        try:

            data = []
            for company in companies:
                company_dict = company.dict()
                company_dict['services'] = ', '.join(company_dict['services'])
                company_dict['pricing'] = '\n'.join([f"{k}: {v}" for k, v in company_dict['pricing'].items()])
                
                review_details = company_dict.get('review_details', {})
                company_dict['total_reviews'] = review_details.get('total_reviews', 0)
                company_dict['highlights'] = '\n'.join(review_details.get('highlights', []))
                company_dict['concerns'] = '\n'.join(review_details.get('concerns', []))
                
                data.append(company_dict)
            
            df = pd.DataFrame(data)
            
            column_order = [
                'name', 'location', 'services', 'pricing', 
                'rating', 'total_reviews', 'highlights', 'concerns',
                'contact', 'website'
            ]
            df = df[column_order]
            
            os.makedirs('reports', exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"reports/market_research_{timestamp}.xlsx"
            
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Market Research')
                
                worksheet = writer.sheets['Market Research']
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(col)
                    ) + 2
                    worksheet.set_column(idx, idx, max_length)
            
            return filename
            
        except Exception as e:
            print(f"Error saving to Excel: {str(e)}")
            raise e 