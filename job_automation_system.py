import requests
from bs4 import BeautifulSoup
import re
# from google.oauth2.credentials import Credentials
# from googleapiclient.discovery import build
# from google.auth.transport.requests import Request
# from google_auth_oauthlib.flow import InstalledAppFlow
import os.path
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import imaplib
import email
from email.header import decode_header
import datetime

# Job search functions
def search_indeed(query, location, num_pages=5):
    jobs = []
    for start in range(0, num_pages * 10, 10):
        url = f"https://ca.indeed.com/jobs?q={query}&l={location}&remotejob=032b3046-06a3-4876-8dfd-474eb5e7ed11&start={start}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        for div in soup.find_all('div', class_='job_seen_beacon'):
            title = div.find('h2', class_='jobTitle').text.strip()
            company = div.find('span', class_='companyName').text.strip()
            link = 'https://ca.indeed.com' + div.find('a')['href']
            jobs.append({'title': title, 'company': company, 'link': link, 'source': 'Indeed'})
        time.sleep(1)  # Respect the website by not sending too many requests too quickly
    return jobs

def search_linkedin(query, location, num_pages=5):
    jobs = []
    for page in range(num_pages):
        url = f"https://www.linkedin.com/jobs/search/?keywords={query}&location={location}&f_WT=2&start={page*25}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        for div in soup.find_all('div', class_='base-card'):
            title = div.find('h3', class_='base-search-card__title').text.strip()
            company = div.find('h4', class_='base-search-card__subtitle').text.strip()
            link = div.find('a', class_='base-card__full-link')['href']
            jobs.append({'title': title, 'company': company, 'link': link, 'source': 'LinkedIn'})
        time.sleep(1)
    return jobs

def search_glassdoor(query, location, num_pages=5):
    jobs = []
    for page in range(1, num_pages + 1):
        url = f"https://www.glassdoor.ca/Job/canada-{query.replace(' ', '-')}-jobs-SRCH_IL.0,6_IN3_KO7,{len(query)+7}_IP{page}.htm?remoteWorkType=1"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        for li in soup.find_all('li', class_='react-job-listing'):
            title = li.find('a', class_='jobLink').text.strip()
            company = li.find('div', class_='emp-info').text.strip()
            link = 'https://www.glassdoor.ca' + li.find('a', class_='jobLink')['href']
            jobs.append({'title': title, 'company': company, 'link': link, 'source': 'Glassdoor'})
        time.sleep(1)
    return jobs

# Job filtering function
def filter_jobs(jobs):
    keywords = ['software engineer', 'backend', 'distributed systems', 'remote']
    filtered_jobs = []
    for job in jobs:
        if any(keyword in job['title'].lower() for keyword in keywords):
            filtered_jobs.append(job)
    return filtered_jobs

def calculate_credibility_score(job):
    score = 0
    reasons = []

    # 1. Company name check
    if job['company']:
        score += 10
        reasons.append("Company name present")
        if len(job['company']) > 1:
            score += 5
            reasons.append("Company name seems valid")
    else:
        reasons.append("No company name")

    # 2. Job title check
    if job['title']:
        score += 10
        reasons.append("Job title present")
        if len(job['title'].split()) > 1:
            score += 5
            reasons.append("Detailed job title")
    else:
        reasons.append("No job title")

    # 3. Description length (if available)
    # if 'description' in job and job['description']:
    #     desc_length = len(job['description'].split())
    #     if desc_length > 100:
    #         score += 15
    #         reasons.append("Detailed job description")
    #     elif desc_length > 50:
    #         score += 10
    #         reasons.append("Adequate job description")
    #     else:
    #         score += 5
    #         reasons.append("Short job description")
    # else:
    #     reasons.append("No job description")

    # 4. Check for suspicious keywords
    # suspicious_keywords = ['urgent', 'immediate start', 'work from home', 'no experience needed', 'earn $']
    # if 'description' in job:
    #     if any(keyword in job['description'].lower() for keyword in suspicious_keywords):
    #         score -= 10
    #         reasons.append("Contains suspicious keywords")

    # 5. Company website check
    # if 'company_url' in job and job['company_url']:
    #     parsed_url = urlparse(job['company_url'])
    #     if parsed_url.scheme and parsed_url.netloc:
    #         score += 10
    #         reasons.append("Valid company website format")
    #         if requests.get(job['company_url']).status_code == 200:
    #             score += 5
    #             reasons.append("Company website is accessible")
    #     else:
    #         reasons.append("Invalid company website format")
    # else:
    #     reasons.append("No company website provided")

    # 6. Job source credibility
    credible_sources = ['LinkedIn', 'Indeed', 'Glassdoor']
    if job['source'] in credible_sources:
        score += 15
        reasons.append(f"Posted on credible job board: {job['source']}")

    # 7. Salary information (if available)
    # if 'salary' in job and job['salary']:
    #     score += 10
    #     reasons.append("Salary information provided")

    # 8. Location check
    # if 'location' in job and job['location']:
    #     score += 5
    #     reasons.append("Location information provided")

    # 9. Required skills check (if available)
    # if 'required_skills' in job and job['required_skills']:
    #     if len(job['required_skills']) > 2:
    #         score += 10
    #         reasons.append("Multiple required skills listed")

    # 10. Company reputation check (simplified version)
    if job['company']:
        company_name = job['company'].lower()
        if company_name in ['google', 'microsoft', 'amazon', 'apple', 'facebook', 'quora']:
            score += 20
            reasons.append("Well-known reputable company")

    # Normalize score to be out of 100
    normalized_score = min(100, max(0, score))

    return normalized_score, reasons

def filter_credible_jobs(jobs, minimum_score=60):
    credible_jobs = []
    for job in jobs:
        score, reasons = calculate_credibility_score(job)
        if score >= minimum_score:
            job['credibility_score'] = score
            job['credibility_reasons'] = reasons
            credible_jobs.append(job)
    return credible_jobs

# Google Sheets functions
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_google_sheets_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('sheets', 'v4', credentials=creds)

def update_sheet(service, spreadsheet_id, range_name, values):
    body = {'values': values}
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id, range=range_name,
        valueInputOption='USER_ENTERED', body=body).execute()

# Email functions
def send_email(subject, body, to_email):
    from_email = "ahsannaveed007@gmail.com"  # Replace with your email
    password = "your_app_password"  # Replace with your app password

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(from_email, password)
    text = msg.as_string()
    server.sendmail(from_email, to_email, text)
    server.quit()

def check_emails():
    email_user = "ahsannaveed007@gmail.com"
    email_pass = "your_app_password"  # Replace with your app password

    # Connect to the inbox
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(email_user, email_pass)
    mail.select('inbox')

    # Search for emails from job applications
    date = (datetime.date.today() - datetime.timedelta(5)).strftime("%d-%b-%Y")
    _, search_data = mail.search(None, f'(SINCE "{date}")')

    for num in search_data[0].split():
        _, data = mail.fetch(num, '(RFC822)')
        _, bytes_data = data[0]

        email_message = email.message_from_bytes(bytes_data)
        subject, encoding = decode_header(email_message["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding)

        # Check if the email is related to a job application
        if "application" in subject.lower() or "interview" in subject.lower():
            print(f"New job-related email: {subject}")
            # Here you can add logic to update your Google Sheet based on the email content

    mail.close()
    mail.logout()

# Main function
def job_search_and_update():
    # Job search
    all_jobs = []
    all_jobs.extend(search_indeed("software engineer backend distributed systems", "Canada"))
    all_jobs.extend(search_linkedin("software engineer backend distributed systems", "Canada"))
    all_jobs.extend(search_glassdoor("software engineer backend distributed systems", "Canada"))

    # Filter jobs
    filtered_jobs = filter_jobs(all_jobs)

    # Filter credible jobs 
    credible_jobs = filter_credible_jobs(filtered_jobs)

    print("ALL JOBS: ", len(all_jobs))
    print("FILTERED JOBS: ", len(filtered_jobs))
    print("CREDIBLE JOBS: ", len(credible_jobs))

    index = 0
    for job in credible_jobs:
        index += 1
        print(index, ")", job['title'], "=>", job['link'])

    # # Update Google Sheet
    # service = get_google_sheets_service()
    # spreadsheet_id = 'your_spreadsheet_id'  # Replace with your Google Sheet ID
    # range_name = 'Sheet1!A2:E'  # Adjust as needed
    # values = [[job['title'], job['company'], job['link'], job['source'], 'Not Applied'] for job in filtered_jobs]
    # update_sheet(service, spreadsheet_id, range_name, values)

    # # Send email notification
    # send_email("New Job Opportunities", 
    #            f"Found {len(filtered_jobs)} new job opportunities. Check your Google Sheet for details.",
    #            "ahsannaveed007@gmail.com")

    # # Check for application-related emails
    # check_emails()

if __name__ == '__main__':
    # Run job search immediately
    job_search_and_update()

    # # Schedule job search to run daily at 9 AM
    # schedule.every().day.at("09:00").do(job_search_and_update)

    # # Keep the script running
    # while True:
    #     schedule.run_pending()
    #     time.sleep(1)