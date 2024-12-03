import pandas as pd
import os
from datetime import datetime
from ..models.research_models import CompanyInfo
from typing import List

class DocumentService:
    @staticmethod
    async def save_to_excel(companies: List[CompanyInfo]) -> str:
        """Save AI course data to Excel file."""
        try:
            # Flatten the course data
            data = []
            for company in companies:
                if not isinstance(company, CompanyInfo):
                    print(f"Warning: Skipping invalid company data: {company}")
                    continue
                    
                company_dict = company.model_dump()
                
                # Create a row for each course
                for course in company_dict['services']:
                    course_data = {
                        'Platform Name': company_dict['name'],
                        'Course Name': course,
                        'Price': company_dict['pricing'].get(course, 'Not available'),
                        'Duration': company_dict.get('course_details', {}).get('durations', {}).get(course, 'Not specified'),
                        'Skill Level': company_dict.get('course_details', {}).get('skill_level', {}).get(course, 'Not specified'),
                        'Certification': 'Yes' if company_dict.get('course_details', {}).get('certification', {}).get(course) else 'No',
                        'Platform Rating': company_dict['rating'],
                        'Total Reviews': company_dict.get('review_details', {}).get('total_reviews', 'Not available'),
                        'Positive Points': '\n'.join(company_dict.get('review_details', {}).get('highlights', [])),
                        'Areas of Improvement': '\n'.join(company_dict.get('review_details', {}).get('concerns', [])),
                        'Website': company_dict.get('website', 'Not available'),
                        'Contact': company_dict.get('contact', 'Not available')
                    }
                    data.append(course_data)
            
            if not data:
                print("Warning: No valid course data to export")
                return "reports/no_data.txt"
                
            df = pd.DataFrame(data)
            
            # Create Excel writer with formatting
            os.makedirs('reports', exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"reports/ai_courses_research_{timestamp}.xlsx"
            
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='AI Courses')
                
                # Get workbook and worksheet objects
                workbook = writer.book
                worksheet = writer.sheets['AI Courses']
                
                # Add formats
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#4F81BD',
                    'font_color': 'white',
                    'border': 1
                })
                
                # Apply header format
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Auto-adjust columns
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(col)
                    ) + 2
                    worksheet.set_column(idx, idx, min(max_length, 50))  # Cap width at 50
                
                # Add filters
                worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)
            
            print(f"\nSuccessfully exported {len(data)} courses to Excel")
            return filename
            
        except Exception as e:
            print(f"Error saving to Excel: {str(e)}")
            # Create an error file instead of raising the exception
            error_file = "reports/export_error.txt"
            os.makedirs('reports', exist_ok=True)
            with open(error_file, 'w') as f:
                f.write(f"Error exporting data: {str(e)}")
            return error_file