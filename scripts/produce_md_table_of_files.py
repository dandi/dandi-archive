#!/usr/bin/env python3

import argparse
import subprocess
from operator import itemgetter

def git_first_commit_date(filename):
    date_str = subprocess.getoutput(f"git log --follow --format=%ai -- {filename} | tail -n 1")
    return date_str.split()[0]  # Return only the date portion, ignoring time and timezone

def git_describe_contains(commit_hash):
    result = subprocess.run(
        ["git", "describe", "--contains", commit_hash],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return result.stdout.strip() if result.returncode == 0 else ""

def git_first_commit_hash(filename):
    return subprocess.getoutput(f"git log --pretty=format:%H -- {filename} | tail -n 1")

def main():
    parser = argparse.ArgumentParser(description="Generate a Markdown table for files in a Git repo.")
    parser.add_argument("--header", type=str, help="Header for the Markdown file.")
    parser.add_argument("-o", "--output", type=str, help="Output Markdown file name.")
    parser.add_argument("files", nargs="+", help="Files to include in the table.")
    args = parser.parse_args()

    output_lines = []
    if args.header:
        output_lines.extend(args.header.split(r'\n'))
    
    headers = ["File", "Originating Date", "Version", "Implementation State", "Date", "Version", "Superseded by"]
    col_widths = [len(h) for h in headers]

    data = []
    
    for filename in args.files:
        if "-" in filename and filename.endswith(".md"):
            date = git_first_commit_date(filename)
            commit_hash = git_first_commit_hash(filename)
            version = git_describe_contains(commit_hash)
            
            col_widths[0] = max(col_widths[0], len(filename))
            col_widths[1] = max(col_widths[1], len(date))
            col_widths[2] = max(col_widths[2], len(version))

            data.append({
                "filename": filename,
                "date": date,
                "version": version
            })

    col_widths[-3] = col_widths[1]
    col_widths[-2] = col_widths[2]
    
    sorted_data = sorted(data, key=itemgetter('date'))

    header_line = "| " + " | ".join([h.ljust(w) for h, w in zip(headers, col_widths)]) + " |"
    separator_line = "| " + " | ".join(["-" * w for w in col_widths]) + " |"

    output_lines.append(header_line)
    output_lines.append(separator_line)

    for entry in sorted_data:
        filename = entry["filename"].ljust(col_widths[0])
        date = entry["date"].ljust(col_widths[1])
        version = entry["version"].ljust(col_widths[2])
        empty_cols = [" " * w for w in col_widths[3:]]
        row_line = "| " + " | ".join([filename, date, version] + empty_cols) + " |"
        output_lines.append(row_line)

    if args.output:
        with open(args.output, "w") as f:
            f.write("\n".join(output_lines) + "\n")
    else:
        print("\n".join(output_lines))

if __name__ == "__main__":
    main()
