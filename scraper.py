#!/usr/bin/env python3
"""
Windows ISO Links Scraper for Massgrave Repository
Extracts Windows version names, builds, languages, and download links from markdown files
"""

import re
import json
import requests
from typing import Dict, List, Any
from datetime import datetime

# Base URLs
BASE_RAW_URL = "https://raw.githubusercontent.com/massgravel/massgrave.dev/refs/heads/main/docs/"

# Files to scrape
MD_FILES = [
    "windows_11_links.md",
    "windows_10_links.md",
    "windows_7_links.md",
    "windows_8.1_links.md",
    "windows_arm_links.md",
    "windows_ltsc_links.md",
    "windows_vista_links.md",
    "windows_xp_links.md"
]


def fetch_markdown_content(filename: str) -> str:
    """Fetch markdown file content from GitHub"""
    url = BASE_RAW_URL + filename
    print(f"Fetching: {url}")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def extract_version_name(tab_item_line: str) -> str:
    """Extract version name from TabItem value attribute"""
    match = re.search(r'value="([^"]+)"', tab_item_line)
    if match:
        return match.group(1)
    return "Unknown"


def extract_build_number(content: str) -> str:
    """Extract build number from markdown content"""
    # Pattern: Build - 26200.6584 or Build - 7601.17514
    match = re.search(r'Build\s*-\s*(\d+(?:\.\d+)*)', content, re.IGNORECASE)
    if match:
        return match.group(1)
    return "Unknown"


def extract_markdown_table_data(table_content: str) -> List[Dict[str, str]]:
    """Extract language, architecture, and links from markdown tables"""
    results = []

    # Split into lines and find table rows
    lines = table_content.split('\n')

    for line in lines:
        # Skip separator lines and header
        if '|:--' in line or line.strip().startswith('| Language'):
            continue

        # Match table rows with data
        if '|' in line and ('x64' in line or 'x86' in line or 'ARM64' in line):
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]

            if len(cells) >= 3:
                language = cells[0]
                arch = cells[1]
                link_cell = cells[2]

                # Extract URL from markdown link [text](url)
                url_match = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', link_cell)
                if url_match:
                    filename = url_match.group(1)
                    url = url_match.group(2)

                    results.append({
                        "language": language,
                        "architecture": arch,
                        "filename": filename,
                        "url": url
                    })

    return results


def parse_windows_versions(content: str) -> List[Dict[str, Any]]:
    """Parse all Windows versions from a markdown file"""
    versions = []

    # Split content by TabItem tags
    tab_items = re.findall(
        r'<TabItem[^>]*value="([^"]+)"[^>]*label="([^"]+)"[^>]*>.*?</TabItem>',
        content,
        re.DOTALL
    )

    for value, label in tab_items:
        # Skip non-version tabs
        if 'Other Versions' in value or 'Other Versions' in label:
            continue

        # Find the content for this TabItem
        pattern = rf'<TabItem[^>]*value="{re.escape(value)}"[^>]*>(.*?)</TabItem>'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            tab_content = match.group(1)

            # Extract build number
            build = extract_build_number(tab_content)

            # Extract table data
            downloads = extract_markdown_table_data(tab_content)

            if downloads:
                version_data = {
                    "version_name": value,
                    "version_label": label,
                    "build": build,
                    "downloads": downloads
                }
                versions.append(version_data)

    return versions


def scrape_all_windows_versions() -> Dict[str, Any]:
    """Scrape all Windows versions from all markdown files"""
    all_data = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "source": "https://github.com/massgravel/massgrave.dev",
        "windows_versions": {}
    }

    for md_file in MD_FILES:
        try:
            print(f"\n{'='*60}")
            print(f"Processing: {md_file}")
            print(f"{'='*60}")

            # Fetch content
            content = fetch_markdown_content(md_file)

            # Parse versions
            versions = parse_windows_versions(content)

            # Determine Windows category
            if 'windows_11' in md_file:
                category = "Windows 11"
            elif 'windows_10' in md_file:
                category = "Windows 10"
            elif 'windows_7' in md_file:
                category = "Windows 7"
            elif 'windows_8.1' in md_file:
                category = "Windows 8.1"
            elif 'windows_arm' in md_file:
                category = "Windows ARM"
            elif 'windows_ltsc' in md_file:
                category = "Windows LTSC"
            elif 'windows_vista' in md_file:
                category = "Windows Vista"
            elif 'windows_xp' in md_file:
                category = "Windows XP"
            else:
                category = md_file.replace('_links.md', '').replace('_', ' ').title()

            if versions:
                all_data["windows_versions"][category] = versions
                print(f"✓ Found {len(versions)} version(s) in {md_file}")
                for v in versions:
                    print(f"  - {v['version_name']} (Build: {v['build']}, {len(v['downloads'])} downloads)")
            else:
                print(f"✗ No versions found in {md_file}")

        except Exception as e:
            print(f"✗ Error processing {md_file}: {str(e)}")
            continue

    return all_data


def main():
    """Main execution function"""
    print("=" * 60)
    print("Windows ISO Links Scraper")
    print("Source: Massgrave GitHub Repository")
    print("=" * 60)

    try:
        # Scrape all data
        data = scrape_all_windows_versions()

        # Save to JSON
        output_file = "windows_iso_links.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*60}")
        print(f"✓ Successfully saved data to {output_file}")
        print(f"✓ Total categories: {len(data['windows_versions'])}")
        print(f"✓ Last updated: {data['last_updated']}")
        print(f"{'='*60}")

        # Print summary
        print("\nSummary:")
        for category, versions in data['windows_versions'].items():
            total_downloads = sum(len(v['downloads']) for v in versions)
            print(f"  {category}: {len(versions)} version(s), {total_downloads} download(s)")

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
