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

# Files to scrape (Windows)
MD_FILES = [
    "windows_11_links.md",
    "windows_10_links.md",
    "windows_7_links.md",
    "windows_8.1_links.md",
    "windows_arm_links.md",
    "windows_ltsc_links.md",
    "windows_vista__links.md",
    "windows_xp_links.md"
]

# Files to scrape (Office)
OFFICE_MD_FILE = "office_msi_links.md"


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


def extract_tabitems_with_content(section: str) -> List[Dict[str, Any]]:
    """Extract TabItem blocks (value, label, inner content) from a section."""
    items: List[Dict[str, Any]] = []
    for value, label, inner in re.findall(r'<TabItem[^>]*value=\"([^\"]+)\"[^>]*label=\"([^\"]+)\"[^>]*>(.*?)</TabItem>', section, re.DOTALL):
        items.append({
            "value": value,
            "label": label,
            "content": inner,
        })
    return items


def parse_headings_versions(content: str) -> List[Dict[str, Any]]:
    """Parse versions from markdown H2 sections when Tabs are not used.

    For files like Windows XP where versions are presented under headings
    like '## Windows XP SP3 VL (x86)', parse the following table.
    """
    versions: List[Dict[str, Any]] = []
    headings = list(re.finditer(r'(?m)^##\s+(.+?)\s*$', content))
    if not headings:
        return versions

    for i, m in enumerate(headings):
        title = m.group(1).strip()
        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(content)
        section = content[start:end]

        downloads = extract_markdown_table_data(section)
        if not downloads:
            continue

        build = extract_build_number(section)
        versions.append({
            "version_name": title,
            "version_label": title,
            "build": build,
            "downloads": downloads,
        })

    return versions


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

    # Fallback for files without MDX Tabs (e.g., Windows XP)
    if not versions:
        versions = parse_headings_versions(content)

    return versions


def parse_office_sections(content: str) -> Dict[str, List[Dict[str, Any]]]:
    """Parse Office MSI markdown grouped by Office year (H2 headings).

    Returns mapping of category (e.g., 'Office 2016') to list of version dicts.
    """
    office_data: Dict[str, List[Dict[str, Any]]] = {}

    # Find H2 headings like '## Office 2016', '## Office 2013', etc.
    headings = list(re.finditer(r'(?m)^##\s+(Office\s+\d{4})\s*$', content))
    if not headings:
        return office_data

    for i, m in enumerate(headings):
        category = m.group(1).strip()
        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(content)
        section = content[start:end]

        tabitems = extract_tabitems_with_content(section)
        versions: List[Dict[str, Any]] = []
        for ti in tabitems:
            downloads = extract_markdown_table_data(ti["content"])
            if not downloads:
                continue
            build = extract_build_number(ti["content"])  # typically Unknown for Office
            versions.append({
                "version_name": ti["value"],
                "version_label": ti["label"],
                "build": build,
                "downloads": downloads,
            })

        if versions:
            office_data[category] = versions

    return office_data


def scrape_all_windows_versions() -> Dict[str, Any]:
    """Scrape all Windows versions from all markdown files"""
    all_data = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "source": "https://github.com/massgravel/massgrave.dev",
        "windows_versions": {},
        "office_versions": {}
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


def scrape_office_versions(all_data: Dict[str, Any]) -> None:
    """Fetch and parse Office MSI links and add to all_data in-place."""
    try:
        print(f"\n{'='*60}")
        print(f"Processing: {OFFICE_MD_FILE}")
        print(f"{'='*60}")

        content = fetch_markdown_content(OFFICE_MD_FILE)
        office_map = parse_office_sections(content)

        if office_map:
            all_data["office_versions"].update(office_map)
            total_versions = sum(len(v) for v in office_map.values())
            print(f"✔ Found {total_versions} Office version(s) across {len(office_map)} categories")
            for category, versions in office_map.items():
                print(f"  - {category}: {len(versions)} version(s)")
        else:
            print("✖ No Office versions found")

    except Exception as e:
        print(f"✖ Error processing {OFFICE_MD_FILE}: {str(e)}")
        # Do not raise; keep Windows data intact


def main():
    """Main execution function"""
    print("=" * 60)
    print("Windows ISO Links Scraper")
    print("Source: Massgrave GitHub Repository")
    print("=" * 60)

    try:
        # Scrape all data
        data = scrape_all_windows_versions()

        # Scrape Office data and merge
        scrape_office_versions(data)

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

        print("\nSummary (Office):")
        for category, versions in data['office_versions'].items():
            total_downloads = sum(len(v['downloads']) for v in versions)
            print(f"  {category}: {len(versions)} version(s), {total_downloads} download(s)")

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
