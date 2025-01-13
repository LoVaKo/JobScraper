import tkinter as tk
from tkinter import ttk, messagebox
import threading
import numpy as np
import pandas as pd
import re
import requests
import string
import time
import random
import datetime
from bs4 import BeautifulSoup
from rapidfuzz import process, fuzz


def scrape_company_names(progress_bar):    
    # Scraping all companies in ICTergezocht client base
    BASE_URL = "https://www.ictergezocht.nl/ict-bedrijven/bedrijf-start-met-{}/"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }

    ictergezocht_data = pd.DataFrame(columns=["company_name", "company_url"])
    total_letters = 26
    # Loop through the alphabet and scrape each page
    for i, letter in enumerate(string.ascii_lowercase):
        url = BASE_URL.format(letter)

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to retrieve page {url}: {e}")
            continue

        soup = BeautifulSoup(response.text, 'html.parser')

        company_links = soup.select('a[href^="https://www.ictergezocht.nl/ict-bedrijven/"]')

        for link in company_links:
            company_name = link.get('title')
            company_url = link['href']

            if company_name and company_url:
                company_name = company_name.replace("Bedrijven ", "").strip()
                ictergezocht_data.loc[len(ictergezocht_data)] = {"company_name": company_name, "company_url": company_url}
        
        # Update the progress bar for company names (50% of the total progress)
        progress = (i + 1) / total_letters * 50  
        progress_bar.after(0, progress_bar.configure, {'value': progress})  # Safe update on the main thread
        progress_bar.after(0, progress_bar.update_idletasks)  

        time.sleep(random.uniform(1, 3))

    return ictergezocht_data
    

def scrape_jobpostings_ictergezocht(data, BASE_URL, progress_bar):
    job_postings_ictergezocht = pd.DataFrame(columns=["company", "title", "url"])
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
        }
    
    total_companies = len(data)
    for i, row in data.iterrows():
        company_url = row["url"]
        url = BASE_URL + company_url

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to retrieve page {url}: {e}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        open_vacs_element = soup.find(id="open_vacs")

        if open_vacs_element:
            data.at[i, "has_openings"] = 1
            jobpostings = open_vacs_element.find_all("h3")

            for job in jobpostings:
                a = job.find("a")
                job_title = a["title"]
                job_url = a["href"]

                new = pd.DataFrame({
                    "company": [row["company_name"]],
                    "title": [job_title],
                    "url": [job_url]
                })

                job_postings_ictergezocht = pd.concat([job_postings_ictergezocht, new], ignore_index=True)
        else:
            data.at[i, "has_openings"] = 0
        
    # Update the progress bar for job postings (50% of the total progress)
    progress = 50 + (i + 1) / total_companies * 50 
    progress_bar.after(0, progress_bar.configure, {'value': progress})  
    progress_bar.after(0, progress_bar.update_idletasks)

    time.sleep(random.uniform(1, 3))

    return job_postings_ictergezocht


def run_script(progress_bar):
    #  Import and clean dataset
    df_top500 = pd.read_excel("data/top500.xlsx")
    df_top500.drop(columns=["Activiteit", "Soort bedrijf", "Omzet (in mln)", "Winst (in mln)", "Aantal mw"], inplace=True)
    df_top500.rename(columns={
        "NR": "id",
        "Bedrijfsnaam": "company_name",
        "ICT Functies (Ja/Nee)":"has_openings",
        "Functies/Zoektermen": "search_results",
        "Bronvermeldingen": "source",
        "Contact": "contact"
    }, 
    inplace=True)
    df_top500["url"] = np.nan
    df_top500 = df_top500.loc[df_top500["contact"].isna()]
    df_top500.drop(columns=["contact"], inplace=True)

    #  Cleaning company names (removing parentheses and anything between them) and sorting them alphabetically
    df_top500["company_name"] = df_top500["company_name"].apply(lambda x: re.sub(r"\(.*?\)", "", x).strip())
    df_top500.sort_values(by="company_name", inplace=True)
    df_top500.head(30)

    #  Scraping companies from website
    ictergezocht_data = scrape_company_names(progress_bar)

    #  Searching for exact matches in company 500
    df_top500["company_name_lower"] = df_top500["company_name"].str.lower()
    ictergezocht_data["company_name_lower"] = ictergezocht_data["company_name"].str.lower()

    for company, url in zip(ictergezocht_data["company_name_lower"], ictergezocht_data["company_url"]):
        if company in df_top500["company_name_lower"].values:
            df_top500.loc[df_top500["company_name_lower"] == company, "source"] = "ictergezocht"
            df_top500.loc[df_top500["company_name_lower"] == company, "url"] = url

    df_top500.loc[~df_top500["source"].isna()]

    #  Search for company names that are very similar for manual review using fuzzy matching
    matches = []
    scores = []
    threshold = 90

    for name in ictergezocht_data["company_name_lower"]:
        best_match, score, _ = process.extractOne(name, df_top500["company_name_lower"], scorer=fuzz.ratio)
        if score == 100:
            matches.append(None)
            scores.append(score)
            continue
        matches.append(best_match if score > threshold else None)
        scores.append(score)

    ictergezocht_data["matched_name"] = matches
    ictergezocht_data["match_score"] = scores
    ictergezocht_data["manual_review"] = (ictergezocht_data["match_score"] > threshold) & (ictergezocht_data["match_score"] < 100)

    df_top500.drop(columns=["company_name_lower"], inplace=True)
    ictergezocht_data.drop(columns=["company_name_lower"], inplace=True)

    df_top500.loc[df_top500["company_name"] == "Infotheek Group", "url"] = ictergezocht_data.loc[ictergezocht_data["company_name"] == "Infotheek Groep", "company_url"].iloc[0]
    df_top500.loc[df_top500["company_name"] == "Infotheek Group", "source"] = "ictergezocht"

    df_top500.loc[df_top500["company_name"] == "Maandag", "url"] = ictergezocht_data.loc[ictergezocht_data["company_name"] == "Maandag®", "company_url"].iloc[0]
    df_top500.loc[df_top500["company_name"] == "Maandag", "source"] = "ictergezocht"

    df_top500.loc[df_top500["company_name"] == "Tembo Group", "url"] = ictergezocht_data.loc[ictergezocht_data["company_name"] == "Tembogroup", "company_url"].iloc[0]
    df_top500.loc[df_top500["company_name"] == "Tembo Group", "source"] = "ictergezocht"

    # Removing url prefix from entries
    URL_PREFIX_ICTERGEZOCHT = "https://www.ictergezocht.nl/ict-bedrijven/"
    df_top500["url"] = df_top500["url"].str.replace(URL_PREFIX_ICTERGEZOCHT, "")
    df_ictergezocht = df_top500[~df_top500["source"].isna()]

    # Scraping jobpostings
    job_postings_ictergezocht = scrape_jobpostings_ictergezocht(df_ictergezocht, URL_PREFIX_ICTERGEZOCHT, progress_bar)
    date = datetime.date.today()
    job_postings_ictergezocht.to_excel(f"data/results_{date}.xlsx")

    # Notify user that the job is done
    messagebox.showinfo("Scraping Complete", "An Excel file with the results has been created.")


def start_scraping(scrape_button, progress_bar):
    # Disable button to prevent multiple clicks
    scrape_button.config(state=tk.DISABLED)

    # Start the script in a separate thread to prevent UI freeze
    threading.Thread(target=run_script, args=(progress_bar,)).start()

def main():
    root = tk.Tk()
    root.title("Job Scraper")
    root.geometry("400x250")
    label = tk.Label(root, text="Welcome to Job Scraper!", font=("Helvetica", 12))
    label.pack(pady=10)
    progress_bar = ttk.Progressbar(root, length=300, mode="determinate", maximum=100)
    progress_bar.pack(pady=10)
    scrape_button = tk.Button(root, text="Start Scraping!", command=lambda: start_scraping(scrape_button, progress_bar) )
    scrape_button.pack(pady=20)
    root.mainloop()

if __name__ == "__main__":
    main()