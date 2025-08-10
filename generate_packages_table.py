"""
python generate_packages_table.py --update-readme
"""

import argparse
import itertools
import re
import sys
from pathlib import Path

import pandas as pd


def parse_numeric_version(text: str) -> tuple:
    """Extract numeric version tuple for sorting."""
    nums = re.findall(r"\d+", text)
    return tuple(int(n) for n in nums)


def extract_packages_from_history(text: str) -> list[dict]:
    """Extract package information from History section."""
    lines = text.splitlines()

    # Find start of History section
    in_history = False
    for i, line in enumerate(lines):
        if line.strip().startswith("## ") and "History" in line:
            in_history = True
            lines = lines[i:]
            break

    if not in_history:
        return []

    packages = []
    current_release_url = None
    current_os = "Linux x86_64"  # default

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Reset on new version
        if line.startswith("### "):
            current_release_url = None
            current_os = "Linux x86_64"

        # Capture Release link
        elif "[Release](" in line:
            match = re.search(r"\[Release\]\(([^)]+)\)", line)
            if match:
                current_release_url = match.group(1)

        # Capture OS heading
        elif line.startswith("#### "):
            current_os = line[5:].strip() or "Linux x86_64"

        # Process table
        elif line.startswith("| Flash-Attention") or line.startswith(
            "|Flash-Attention"
        ):
            # Skip header and separator
            i += 2

            # Process table rows
            while i < len(lines):
                row_line = lines[i].strip()
                if not row_line.startswith("|") or not row_line:
                    break

                # Parse table row
                cells = [c.strip() for c in row_line.split("|")]
                cells = [c for c in cells if c]  # Remove empty cells

                if len(cells) >= 4:
                    fa_versions = [v.strip() for v in cells[0].split(",") if v.strip()]
                    py_versions = [v.strip() for v in cells[1].split(",") if v.strip()]
                    pt_versions = [v.strip() for v in cells[2].split(",") if v.strip()]
                    cu_versions = [v.strip() for v in cells[3].split(",") if v.strip()]

                    # Generate all combinations
                    for fa, py, pt, cu in itertools.product(
                        fa_versions, py_versions, pt_versions, cu_versions
                    ):
                        packages.append(
                            {
                                "Flash-Attention": fa,
                                "Python": py,
                                "PyTorch": pt,
                                "CUDA": cu,
                                "OS": current_os,
                                "package": current_release_url,
                            }
                        )

                i += 1
            continue

        i += 1

    return packages


def sort_packages(df: pd.DataFrame) -> pd.DataFrame:
    """Sort packages with custom priority."""

    # Add sorting keys
    # Flash-Attention: descending order (newer versions first)
    df["fa_sort"] = df["Flash-Attention"].apply(
        lambda x: tuple(-v for v in parse_numeric_version(x))
    )
    df["os_sort"] = df["OS"].str.lower()
    # Python, PyTorch, CUDA: descending order (newer versions first)
    df["py_sort"] = df["Python"].apply(
        lambda x: tuple(-v for v in parse_numeric_version(x))
    )
    df["pt_sort"] = df["PyTorch"].apply(
        lambda x: tuple(-v for v in parse_numeric_version(x))
    )
    df["cu_sort"] = df["CUDA"].apply(
        lambda x: tuple(-v for v in parse_numeric_version(x))
    )

    # Package sort: extract version from URL, newer first
    def package_sort_key(url):
        if pd.isna(url) or not url:
            return (1, tuple())  # No URL comes last

        tag_match = re.search(r"/tag/([^/]+)$", str(url))
        if not tag_match:
            return (1, tuple())

        tag = tag_match.group(1)
        version_tuple = parse_numeric_version(tag)
        return (0, tuple(-v for v in version_tuple))  # Negate for descending

    df["pkg_sort"] = df["package"].apply(package_sort_key)

    # Sort by priority: Flash-Attention > OS > Python > PyTorch > CUDA > package
    df_sorted = df.sort_values(
        ["fa_sort", "os_sort", "py_sort", "pt_sort", "cu_sort", "pkg_sort"]
    )

    # Drop sorting columns
    return df_sorted.drop(
        columns=["fa_sort", "os_sort", "py_sort", "pt_sort", "cu_sort", "pkg_sort"]
    )


def merge_duplicate_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Merge rows with duplicate Flash-Attention, Python, PyTorch, CUDA, OS values."""
    # Group by all columns except 'package'
    group_cols = ["Flash-Attention", "Python", "PyTorch", "CUDA", "OS"]

    def combine_packages(group):
        # Get unique non-null packages
        packages = [pkg for pkg in group["package"].dropna().unique() if pkg]

        # Take the first row as base
        result = group.iloc[0].copy()

        # Combine packages into a list
        result["package"] = packages if packages else [None]

        return result

    # Group and combine
    merged_df = df.groupby(group_cols, as_index=False).apply(
        combine_packages, include_groups=False
    )

    # Reset index to clean up
    merged_df = merged_df.reset_index(drop=True)

    return merged_df


def generate_markdown_table_by_os(df: pd.DataFrame) -> str:
    """Generate markdown tables grouped by OS and Flash-Attention version."""
    if df.empty:
        return ""

    all_sections = []

    # Group by OS and sort each group
    for os_name in sorted(df["OS"].unique()):
        os_df = df[df["OS"] == os_name].copy()

        # Re-sort within each OS group to ensure Flash-Attention is in descending order
        os_df["fa_sort"] = os_df["Flash-Attention"].apply(
            lambda x: tuple(-v for v in parse_numeric_version(x))
        )
        os_df["py_sort"] = os_df["Python"].apply(
            lambda x: tuple(-v for v in parse_numeric_version(x))
        )
        os_df["pt_sort"] = os_df["PyTorch"].apply(
            lambda x: tuple(-v for v in parse_numeric_version(x))
        )
        os_df["cu_sort"] = os_df["CUDA"].apply(
            lambda x: tuple(-v for v in parse_numeric_version(x))
        )

        # Sort by Flash-Attention > Python > PyTorch > CUDA
        os_df = os_df.sort_values(["fa_sort", "py_sort", "pt_sort", "cu_sort"])
        os_df = os_df.drop(columns=["fa_sort", "py_sort", "pt_sort", "cu_sort"])

        # Create OS section header
        os_lines = [f"### {os_name}", ""]

        # Group by Flash-Attention version within each OS
        fa_versions = []
        for fa_version in os_df["Flash-Attention"].unique():
            fa_df = os_df[os_df["Flash-Attention"] == fa_version].copy()

            # Re-sort by Python > PyTorch > CUDA within each Flash-Attention version
            fa_df["py_sort"] = fa_df["Python"].apply(
                lambda x: tuple(-v for v in parse_numeric_version(x))
            )
            fa_df["pt_sort"] = fa_df["PyTorch"].apply(
                lambda x: tuple(-v for v in parse_numeric_version(x))
            )
            fa_df["cu_sort"] = fa_df["CUDA"].apply(
                lambda x: tuple(-v for v in parse_numeric_version(x))
            )
            fa_df = fa_df.sort_values(["py_sort", "pt_sort", "cu_sort"])
            fa_df = fa_df.drop(columns=["py_sort", "pt_sort", "cu_sort"])

            # Create collapsible table for this Flash-Attention version
            table_lines = [
                "| Python | PyTorch | CUDA | package |",
                "| ------ | ------- | ---- | ------- |",
            ]

            for _, row in fa_df.iterrows():
                packages = row["package"]

                # Handle case where packages is a list
                if isinstance(packages, list):
                    if packages and any(pd.notna(pkg) and pkg for pkg in packages):
                        # Create numbered release links
                        package_links = []
                        for i, pkg in enumerate(packages, 1):
                            if pd.notna(pkg) and pkg:
                                package_links.append(f"[Release{i}]({pkg})")
                        package_cell = ", ".join(package_links)
                    else:
                        package_cell = "-"
                else:
                    # Handle single package (backward compatibility)
                    package_cell = (
                        f"[Release]({packages})"
                        if pd.notna(packages) and packages
                        else "-"
                    )

                line = f"| {row['Python']} | {row['PyTorch']} | {row['CUDA']} | {package_cell} |"
                table_lines.append(line)

            # Create collapsible section for this Flash-Attention version
            fa_section = [
                f"#### Flash-Attention {fa_version}",
                "",
                "<details>",
                f"<summary>Packages for Flash-Attention {fa_version}</summary>",
                "",
                "\n".join(table_lines),
                "",
                "</details>",
                "",
            ]

            fa_versions.extend(fa_section)

        os_lines.extend(fa_versions)
        all_sections.extend(os_lines)

    return "\n".join(all_sections)


def generate_markdown_table(df: pd.DataFrame) -> str:
    """Generate markdown table from DataFrame (legacy function for backward compatibility)."""
    lines = [
        "| Flash-Attention | Python | PyTorch | CUDA | OS | package |",
        "| --------------- | ------ | ------- | ------ | ---- | ------- |",
    ]

    for _, row in df.iterrows():
        packages = row["package"]

        # Handle case where packages is a list
        if isinstance(packages, list):
            if packages and any(pd.notna(pkg) and pkg for pkg in packages):
                # Create numbered release links
                package_links = []
                for i, pkg in enumerate(packages, 1):
                    if pd.notna(pkg) and pkg:
                        package_links.append(f"[Release{i}]({pkg})")
                package_cell = ", ".join(package_links)
            else:
                package_cell = "-"
        else:
            # Handle single package (backward compatibility)
            package_cell = (
                f"[Release]({packages})" if pd.notna(packages) and packages else "-"
            )

        line = f"| {row['Flash-Attention']} | {row['Python']} | {row['PyTorch']} | {row['CUDA']} | {row['OS']} | {package_cell} |"
        lines.append(line)

    return "\n".join(lines)


def update_readme_packages_section(readme_path: Path, packages_markdown: str) -> None:
    """Update the Packages section in README.md with new content."""
    try:
        with readme_path.open("r", encoding="utf-8") as f:
            content = f.read()

        # Find the Packages section
        packages_start = content.find("## Packages")
        if packages_start == -1:
            raise ValueError("Packages section not found in README.md")

        # Find the end of Packages section (next ## section or History section)
        packages_end = content.find("## History", packages_start)
        if packages_end == -1:
            # If no History section found, look for any other ## section
            remaining_content = content[packages_start + len("## Packages") :]
            next_section = remaining_content.find("\n## ")
            if next_section != -1:
                packages_end = packages_start + len("## Packages") + next_section
            else:
                packages_end = len(content)

        # Replace the Packages section
        new_content = (
            content[:packages_start]
            + "## Packages\n\n"
            + packages_markdown
            + "\n\n"
            + content[packages_end:]
        )

        # Write back to file
        with readme_path.open("w", encoding="utf-8") as f:
            f.write(new_content)

    except Exception as e:
        raise RuntimeError(f"Failed to update README.md: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a one-row-per-package Markdown table from the History section of a README.md"
    )
    parser.add_argument(
        "readme",
        nargs="?",
        type=Path,
        default=Path("README.md"),
        help="Path to README.md (default: README.md)",
    )
    parser.add_argument(
        "--update-readme",
        action="store_true",
        help="Update the Packages section in README.md instead of printing to stdout",
    )
    args = parser.parse_args()

    try:
        with args.readme.open("r", encoding="utf-8") as f:
            text = f.read()

        packages = extract_packages_from_history(text)

        if not packages:
            print("No packages found in History section", file=sys.stderr)
            return

        df = pd.DataFrame(packages)
        df_sorted = sort_packages(df)
        df_merged = merge_duplicate_rows(df_sorted)
        markdown = generate_markdown_table_by_os(df_merged)

        if args.update_readme:
            # Update the README.md file
            update_readme_packages_section(args.readme, markdown)
            print(f"Updated Packages section in {args.readme}")
        else:
            # Print to stdout (original behavior)
            print(markdown)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
