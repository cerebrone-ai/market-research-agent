# Market Research Automation

This application automates the process of conducting market research by generating search terms, gathering company data, and exporting the results to an Excel file. It leverages advanced language models to analyze topics and extract structured information from search results.

## Features

- **Generate Search Terms**: Automatically create focused search terms based on a given research topic.
- **Gather Company Data**: Extract detailed information about companies, including products, pricing, reviews, and market details.
- **Export to Excel**: Save the gathered data into an Excel file for easy analysis and reporting.

## Prerequisites

- Python 3.8 or higher
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/reacredence/market-research.git
   cd market-research
   ```

2. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables for API keys:

   - `OPENAI_API_KEY`: Your OpenAI API key.
   - `TAVILY_API_KEY`: Your Tavily API key.

   You can set these in your shell or in a `.env` file.

## Usage

1. Run the application:

   ```bash
   python main.py
   ```

2. Follow the prompts to enter the research topic.

3. The application will generate search terms, gather company data, and export the results to an Excel file in the `reports` directory.

## Configuration

- **Models**: The application uses different language models for various tasks. You can configure these in `src/config.py`.
- **Output Directory**: The default directory for reports is `reports`. You can change this in `src/config.py`.

## Project Structure

- `src/config.py`: Configuration for API keys and model settings.
- `src/models/research_models.py`: Data models for research terms and company information.
- `src/services`: Contains services for interacting with language models and saving data.
- `src/workflow`: Workflow logic for generating search terms and gathering data.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.
