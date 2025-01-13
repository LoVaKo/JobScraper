# Job Scraper
A web scraping tool that searches for job postings on ICTergezocht.nl based on a list of companies provided by an account manager. The script stores the results in an organized format for later analysis.

This project provides both an interactive notebook and a script to turn the scraper into an executable with a simple GUI.

## How to run the scraper
Make sure you have Conda installed and are in the project directory for `JobScraper`.

1. Create Conda environment based on `environment.yml`
2. Activate environment
3. Run script
4. View results in `data` folder.
   
   ```bash
   conda env create --file environment.yml
   conda activate job_scraper
   python3 script_for_executable.py
   ```


## Project Structure
```
JobScraper
├── README.md
├── data
│   ├── ictergezocht_companies.csv
│   ├── results_2025-01-10.xlsx
│   ├── results_2025-01-13.xlsx
│   └── top500.xlsx
├── environment.yml
├── notebook.ipynb
└── script_for_executable.py
```
#### data
- **ictergezocht_companies.csv**: Scraping results for all companies on the website
- **top500.xlsx**: Original file with company info `CONTACT COLUMN HAS BEEN LEFT EMPTY FOR PRIVACY PURPOSES`
- **results**: Generated results: Job postings from the companies in the base file for a certain date.
  
#### environment.yml
Configuration for Conda environment to run the notebook and script.  

#### notebook.ipynb
Jupyter notebook, used to figure out how to make the scraper work.

#### script_for_executable.py
Script to turn the scraper into an executable for a foolproof scraping experience. Includes a simple GUI with loading bar because the process of scraping takes a few minutes. Drawback of using the script is that there is no possibility for manual review of company names. Since they don't change too often, I decided this would probably not be a big problem.

