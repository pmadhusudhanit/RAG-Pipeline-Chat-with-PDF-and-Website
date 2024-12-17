import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import json
import pandas as pd

# Scrape the main page for basic details and links to detailed profiles
def scrape_main_page(url):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    faculty_data = []
    cards = soup.find_all("div", class_="faculty-card")

    for card in cards:
        faculty = {}
        name_element = card.find("h2").find("a") if card.find("h2") else None
        faculty['name'] = name_element.string.strip() if name_element and name_element.string else "N/A"
        faculty['profile_link'] = name_element.get("href") if name_element else "N/A"

        personal_webpage_element = card.find("a", string="Personal Webpage")
        faculty['personal_webpage'] = personal_webpage_element.get("href") if personal_webpage_element else "N/A"

        email_element = card.find("p", string=lambda s: s and "Email:" in s)
        faculty['email'] = email_element.string.replace("Email:", "").replace("[at]", "@").replace("[dot]", ".").strip() if email_element else "N/A"
        
        phone_element = card.find("p", string=lambda s: s and "Phone:" in s)
        faculty['phone'] = phone_element.string.replace("Phone:", "").strip() if phone_element else "N/A"

        if faculty['name'] == "N/A" or faculty['email'] == "N/A" or faculty['phone'] == "N/A":
            continue

        faculty_data.append(faculty)

    return faculty_data

# Scrape detailed faculty profile for additional information
def scrape_profile_page(profile_url):
    if profile_url in ["#", "N/A"]:
        print(f"Skipping invalid profile URL: {profile_url}")
        return {}

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(profile_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        details = {}
        expertise = soup.find("div", id="expertise-view")
        details["expertise"] = expertise.text.strip() if expertise else "N/A"

        qualification = soup.find("div", id="list_panel_qualification")
        qualifications = []
        if qualification:
            for li in qualification.find_all("li", id="qualification-view"):
                year = li.find("time").text.strip() if li.find("time") else "N/A"
                degree = li.find("h2").text.strip() if li.find("h2") else "N/A"
                institution = li.find("p").text.strip() if li.find("p") else "N/A"
                qualifications.append(f"{year}: {degree} - {institution}")
        details["qualification"] = "\n".join(qualifications) if qualifications else "N/A"

        experience = soup.find("div", id="list_panel_experience")
        experiences = []
        if experience:
            for li in experience.find_all("li", id="edit-experience-view"):
                year = li.find("time").text.strip() if li.find("time") else "N/A"
                position = li.find("h2").text.strip() if li.find("h2") else "N/A"
                details_text = " ".join(p.text.strip() for p in li.find_all("p") if p.text.strip())
                experiences.append(f"{year}: {position} - {details_text}")
        details["experience"] = "\n".join(experiences) if experiences else "N/A"

        return details
    except Exception as e:
        print(f"Failed to scrape profile at {profile_url}: {e}")
        return {}

# Scrape faculty data and combine with detailed profile information
def scrape_faculty_data(main_url):
    faculty_list = scrape_main_page(main_url)

    final_data = []
    for faculty in faculty_list:
        if faculty.get("profile_link") not in ["#", "N/A"]:
            print(f"Scraping profile for: {faculty['name']}")
            profile_details = scrape_profile_page(faculty["profile_link"])
            faculty.update(profile_details)
        else:
            print(f"Skipping profile for: {faculty['name']} (Invalid URL: {faculty['profile_link']})")

        if all(value != "N/A" for value in faculty.values()):
            final_data.append(faculty)

    return final_data

# Create PDF from faculty data
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, "Faculty Details", 0, 1, "C", fill=True)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

    def faculty_details(self, faculty):
        self.set_font("Arial", "B", 12)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 10, faculty.get("name", "N/A"), 0, 1, "L", fill=True)

        self.set_font("Arial", "", 10)
        self.multi_cell(0, 10, f"Profile Link: {faculty.get('profile_link', 'N/A')}", align="L")
        self.multi_cell(0, 10, f"Personal Webpage: {faculty.get('personal_webpage', 'N/A')}", align="L")

        self.set_font("Arial", "B", 10)
        self.cell(0, 8, "Contact Information:", ln=True)
        self.set_font("Arial", "", 10)
        self.multi_cell(0, 10, f"Email: {faculty.get('email', 'N/A')}", align="L")
        self.multi_cell(0, 10, f"Phone: {faculty.get('phone', 'N/A')}", align="L")

        self.set_font("Arial", "B", 10)
        self.cell(0, 8, "Expertise:", ln=True)
        self.set_font("Arial", "", 10)
        self.multi_cell(0, 10, faculty.get("expertise", "N/A"), align="L")

        self.set_font("Arial", "B", 10)
        self.cell(0, 8, "Qualification:", ln=True)
        self.set_font("Arial", "", 10)
        self.multi_cell(0, 10, faculty.get("qualification", "N/A"), align="L")

        self.set_font("Arial", "B", 10)
        self.cell(0, 8, "Experience:", ln=True)
        self.set_font("Arial", "", 10)
        self.multi_cell(0, 10, faculty.get("experience", "N/A"), align="L")

        self.ln(5)
        self.set_fill_color(200, 200, 200)
        self.cell(0, 1, "", 0, 1, "C", fill=True)
        self.ln(5)

# Scrape and generate PDF
main_page_url = "https://cse.iitrpr.ac.in/?page_id=75"  # Replace with actual URL
data = scrape_faculty_data(main_page_url)

pdf = PDF()
pdf.add_page()

for faculty in data:
    pdf.faculty_details(faculty)

pdf.output("faculty_details_from_json.pdf")
print("PDF generated: faculty_details_from_json.pdf")

# Scrape additional links and save to CSV
def scrape_main_and_links(base_url):
    response = requests.get(base_url)
    if response.status_code != 200:
        print(f"Failed to retrieve the main webpage. Status code: {response.status_code}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    main_page_text = soup.get_text()
    print("\n--- Content from the Main Page ---\n")
    print(main_page_text[:500])

    data = [{"Link": base_url, "Content": main_page_text.strip()}]
    links = soup.find_all('a', href=True)
    link_urls = [link['href'] for link in links]
    absolute_links = [url if url.startswith('http') else base_url + url for url in link_urls]

    print("\n--- Available Links ---")
    for i, link in enumerate(absolute_links):
        print(f"{i + 1}: {link}")

    selected_indices = input("\nEnter the numbers of the links you want to scrape (comma-separated): ")
    selected_links = [absolute_links[int(idx) - 1] for idx in selected_indices.split(",") if idx.strip().isdigit()]

    for i, link in enumerate(selected_links):
        try:
            print(f"\nScraping link {i + 1}/{len(selected_links)}: {link}")
            link_response = requests.get(link)
            if link_response.status_code == 200:
                link_soup = BeautifulSoup(link_response.text, 'html.parser')
                link_text = link_soup.get_text()
                data.append({"Link": link, "Content": link_text.strip()})
            else:
                print(f"Failed to retrieve {link}. Status code: {link_response.status_code}")
        except Exception as e:
            print(f"Error scraping {link}: {e}")

    df = pd.DataFrame(data)
    output_file = "scraped_data.csv"
    df.to_csv(output_file, index=False)
    print(f"\nData saved to {output_file}")

base_url = "https://www.svec.education/training-and-placements/"  # Replace with your target website
scrape_main_and_links(base_url)
