import json
import os
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import requests

download_page = 'https://www.win-rar.com/download.html?&L=0'
download_language = 'Chinese Traditional'
sc_download_url = f'https://www.win-rar.com/fileadmin/winrar-versions/sc'
sc_download_type = 'wrr'
data_file = os.path.abspath(os.path.dirname(__file__)) + "/data.json"
introduce_file = os.path.abspath(os.path.dirname(__file__)) + "/introduce.md"
readme_file = os.getcwd() + "/README.md"


def get_latest_url():
    print(f"[GetLatestUrl] Getting download url for {download_language} version from {download_page}")
    response = requests.get(download_page)
    # If the request was successful (HTTP status code 200)
    if response.status_code == 200:
        print("[GetLatestUrl] Successfully retrieved the download page")
        # Use BeautifulSoup to parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the <a> element that contains the text 'Chinese Traditional 64'
        # and get its href attribute to find the download link
        target_link_64 = None
        target_link_32 = None
        target_version_64 = download_language + ' 64'
        target_version_32 = download_language + ' 32'

        for a_tag in soup.find_all('a', string=lambda text: target_version_64 in text if text else False):
            target_link_64 = a_tag.get('href')
            print(f"[GetLatestUrl] Found download link for {download_language} 64-bit version: {target_link_64}")
            break
        for a_tag in soup.find_all('a', string=lambda text: target_version_32 in text if text else False):
            target_link_32 = a_tag.get('href')
            print(f"[GetLatestUrl] Found download link for {download_language} 32-bit version: {target_link_32}")
            break

        # Return the found link
        return {'64': target_link_64, '32': target_link_32}
    else:
        print('[GetLatestUrl] Failed to get the download url')
        return None


def get_sc_file_name(link):
    print(f"[GetFileName] Getting file name from: {link}")
    parsed_url = urlparse(link)
    path = parsed_url.path

    # Extract the filename from the path
    filename = path.split('/')[-1]
    filename = filename.replace('tc', 'sc')
    print(f"[GetFileName] Extracted file name for Simplified Chinese: {filename}")
    return filename


def get_version_number(filename):
    # Pattern to match the version number
    # This pattern assumes the version format is always three digits (major version 7, minor version 00)
    # followed by optional characters (like 'sc' in this case)
    pattern = re.compile(r'winrar-x\d{2,3}-(\d)(\d{2})sc\.exe')

    # Search for the pattern in the filename
    match = pattern.search(filename)
    if match:
        # Format the version number as Major.Minor
        print(f"[GetVersion] Found version number: {match.group(1)}.{match.group(2)} for {filename}")
        version = f"{int(match.group(1))}.{match.group(2)}"
        return version
    else:
        return "Version not found"

def get_last_modified(link):
    print(f"[GetDate] Checking Last-Modified header for: {link}")
    response = requests.head(link)

    if response.status_code == 200:
        # Extract the Last-Modified header
        last_modified = response.headers.get('Last-Modified')
    if last_modified:
        # Parse the Last-Modified date string
        last_modified_date = datetime.strptime(last_modified, '%a, %d %b %Y %H:%M:%S GMT')
        # Format the date into YYYYMMDD format
        # formatted_date = last_modified_date.strftime('%Y%m%d')
        print(f"[GetDate] Get Last-Modified Date: {last_modified_date}")
        return last_modified_date
    else:
        print("[GetDate] Last-Modified header not found")
        return None


def get_sc_url(date, filename, x64_date = None):
    # Deduce the base URL from the provided filename
    base_url = f"{sc_download_url}/sc{date.strftime('%Y%m%d')}/{sc_download_type}/{filename}"

    if x64_date:
        base_url = f"{sc_download_url}/sc{x64_date}/{sc_download_type}/{filename}"
        date -= timedelta(days=1)

    print(f"[GetScUrl] Starting with base URL: {base_url}")

    for _ in range(50):
        # Check the current URL
        print(f"[GetScUrl] Checking URL: {base_url}")
        response = requests.head(base_url)

        if response.status_code == 200:
            print(f"[GetScUrl] Found valid URL: {base_url}")
            return [base_url, date.strftime('%Y%m%d')]
        else:
            # If the URL does not exist, decrement the date by one day and update the URL
            date += timedelta(days=1)
            base_url = f"{sc_download_url}/sc{date.strftime('%Y%m%d')}/{sc_download_type}/{filename}"
            print(f"[GetScUrl] URL not valid, trying next day: {base_url}")

    # If we exit the loop, it means a valid URL was found or we've hit some limit
    print("[GetScUrl] Could not find a valid URL.")
    return None

def read_data():
    with open(data_file, 'r', encoding='utf-8') as file:
        data = json.load(file)
        return data

def write_data(data):
    with open(data_file, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

def if_new_version(json, version):
    if version in json:
        return False
    return True

def md_latest_version(json):
    max_version = max(json.items(), key=lambda x: x[1]['date'])
    markdown_text = f"""## 当前最新版本\n### {max_version[0]}\n**32 位：** {max_version[1]['32']}  \n**64 位：** {max_version[1]['64']}"""
    return markdown_text

def md_all_version(json):
    markdown_text = "## 历史版本\n"
    for version in json:
        text = f"### {version}\n**32 位：** {json[version]['32']}  \n**64 位：** {json[version]['64']}  \n\n"
        if "available" in json[version] and not json[version]["available"]:
            text = f"### ~~{version}~~\n~~**32 位：** {json[version]['32']}~~  \n~~**64 位：** {json[version]['64']}~~  \n\n"
        markdown_text += text
    return markdown_text

def md_introduce():
    with open(introduce_file, 'r', encoding='utf-8') as file:
        return file.read()

def md_all(json):
    markdown_text = md_introduce()+"\n"
    markdown_text += md_latest_version(json)+"\n\n"
    markdown_text += md_all_version(json)
    with open(readme_file, 'w', encoding='utf-8') as file:
        file.write(markdown_text)

def main():
    urls = get_latest_url()
    url_64 = urls['64']
    url_32 = urls['32']
    sc_filename_64 = get_sc_file_name(url_64)
    sc_filename_32 = get_sc_file_name(url_32)
    version_64 = get_version_number(sc_filename_64)
    # version_32 = get_version_number(sc_filename_32)
    data = read_data()
    if if_new_version(data, version_64):
        date_64 = get_last_modified(url_64)
        date_32 = get_last_modified(url_32)
        [sc_url_64, src_date_64] = get_sc_url(date_64, sc_filename_64)
        [sc_url_32, _] = get_sc_url(date_32, sc_filename_32, src_date_64)
        if version_64 not in data:
            data[version_64] = {}
        data[version_64]["64"] = sc_url_64
        data[version_64]["32"] = sc_url_32
        data[version_64]["date"] = src_date_64
        write_data(data)
    else:
        print("No new version found")
    md_all(data)

if __name__ == '__main__':
    main()
