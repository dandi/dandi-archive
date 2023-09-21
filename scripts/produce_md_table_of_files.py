#!/usr/bin/env python3

import argparse
import subprocess
import os
from operator import itemgetter

def git_first_commit_date(filename):
    return subprocess.getoutput(f"git log --follow --format=%ai -- {filename} | tail -n 1")

def git_describe_contains(commit_hash):
    return subprocess.getoutput(f"git describe --contains {commit_hash}")

def git_first_commit_hash(filename):
    return subprocess.getoutput(f"git log --pretty=format:%H -- {filename} | tail -n 1")

def main():
    parser = argparse.ArgumentParser(description="Generate a Markdown table for files in a Git repo.")
    parser.add_argument("--header", type=str, required=True, help="Header for the Markdown file.")
    parser.add_argument("-o", "--output", type=str, help="Output Markdown file name.")
    parser.add_argument("files", nargs="+", help="Files to include in the table.")
    args = parser.parse_args()

    output_lines = []
    output_lines.append(args.header + "\n")
    output_lines.append("| File | Date | Version | Implemented State | Date | Version |")
    output_lines.append("| ---- | ---- | ------- | ----------------- | ---- | ------- |")

    data = []
    
    for filename in args.files:
        if "-" in filename and filename.endswith(".md"):
            date = git_first_commit_date(filename)
            commit_hash = git_first_commit_hash(filename)
            version = git_describe_contains(commit_hash)
            data.append({
                "filename": filename,
                "date": date,
                "version": version
            })
    
    sorted_data = sorted(data, key=itemgetter('date'))

    for entry in sorted_data:
        filename = entry["filename"]
        date = entry["date"]
        version = entry["version"]
        output_lines.append(f"| [{filename}](./{filename}) | {date} | {version} |  |  |  |")

    if args.output:
        with open(args.output, "w") as f:
            f.write("\n".join(output_lines) + "\n")
    else:
        print("\n".join(output_lines))

if __name__ == "__main__":
    main()
