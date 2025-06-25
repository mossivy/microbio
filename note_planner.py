#!/usr/bin/env python3
"""
Note-Based Study Planner - Generates study plans based on vimwiki notes and importance levels
"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import random


class NoteStudyPlanner:
    """Generates study plans specifically based on note content and importance"""

    def __init__(self, notes_dir="notes/", metadata_file="data/study_metadata.json"):
        self.notes_dir = notes_dir
        self.metadata_file = metadata_file
        self.metadata = self._load_metadata()

    def _load_metadata(self):
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, "r") as f:
                return json.load(f)
        return {}

    def _save_metadata(self):
        os.makedirs(os.path.dirname(self.metadata_file), exist_ok=True)
        with open(self.metadata_file, "w") as f:
            json.dump(self.metadata, f, indent=2)

    def parse_note_file(self, file_path):
        """Parse a vimwiki file and extract structure with importance"""
        with open(file_path, "r") as f:
            content = f.read()

        result = {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "main_topic": "",
            "subsections": {},
            "tags": [],
            "global_importance": "medium",  # default for entire file
        }

        lines = content.split("\n")
        current_section = None

        for i, line in enumerate(lines):
            # IMPORTANT FIX 1: The regex for subsection is now checked FIRST.
            # This prevents any ambiguity. If it's a subsection, it's handled here and the loop continues.
            section_match = re.match(r"^==\s*(.+?)\s*==.*$", line)
            if section_match:
                section_title = section_match.group(1).strip()

                # Default importance
                importance = result["global_importance"]

                # Check for importance tag on the same line, e.g., == Section == {importance:high}
                importance_match = re.search(r"\{importance:(high|medium|low)\}", line)
                if importance_match:
                    importance = importance_match.group(1)

                current_section = section_title
                result["subsections"][current_section] = {
                    "importance": importance,
                    "content_lines": [],
                    "key_terms": [],
                    "line_count": 0,
                }
                continue

            # IMPORTANT FIX 2: This now uses `elif`. It will only be checked if the line is NOT a subsection.
            # The regex is also made more specific to ensure it doesn't match '==' at the start.
            topic_match = re.match(
                r"^=\s([^=].*[^=])\s=$", line.strip()
            )  # This is a more robust regex
            if topic_match:
                result["main_topic"] = topic_match.group(1).strip()
                # A main topic resets the current section
                current_section = None
                continue

            # Extract tags (example: :tag1:tag2:)
            tag_match = re.match(r"^:(.+):$", line.strip())
            if tag_match:
                result["tags"].extend(tag_match.group(1).strip().split(":"))
                continue

            # The rest of the logic for handling content remains the same
            if current_section and line.strip():
                result["subsections"][current_section]["content_lines"].append(line)
                result["subsections"][current_section]["line_count"] += 1

                if "::" in line:
                    term = (
                        line.split("::")[0].strip().replace("* ", "").replace("- ", "")
                    )
                    result["subsections"][current_section]["key_terms"].append(term)

        return result

    def calculate_study_priority(self, section_data, file_metadata):
        """Calculate priority score based on importance, content, and review history"""
        importance_weights = {"high": 10, "medium": 5, "low": 2}
        base_score = importance_weights.get(section_data["importance"], 5)

        # Content complexity factor (more content = higher priority)
        content_factor = min(section_data["line_count"] / 10, 2.0)  # Cap at 2x

        # Review history factor
        review_factor = 1.0
        if "last_reviewed" in file_metadata:
            days_since_review = (
                datetime.now()
                - datetime.strptime(file_metadata["last_reviewed"], "%Y-%m-%d")
            ).days
            if days_since_review > 7:
                review_factor = min(
                    days_since_review / 7, 3.0
                )  # Up to 3x for old content
        else:
            review_factor = 2.0  # Never reviewed = high priority

        # Key terms factor (more terms = higher priority)
        terms_factor = 1 + (len(section_data["key_terms"]) * 0.1)

        total_score = base_score * content_factor * review_factor * terms_factor
        return round(total_score, 2)

    def generate_study_plan(
        self,
        target_sections=5,
        focus_high_importance=True,
        randomize=False,
        debug=False,
    ):
        """Generate a study plan based on note analysis"""

        if not os.path.exists(self.notes_dir):
            print(f"Notes directory '{self.notes_dir}' not found!")
            return

        all_sections = []
        files_processed = 0

        # Parse all note files (including in subdirectories)
        for file_path in Path(self.notes_dir).rglob("*.wiki"):
            if debug:
                print(f"Processing: {file_path}")

            note_data = self.parse_note_file(file_path)
            files_processed += 1

            if debug:
                print(f"  Main topic: '{note_data['main_topic']}'")
                print(f"  Subsections: {list(note_data['subsections'].keys())}")

            file_key = note_data["file_name"]

            # Get metadata for this file
            file_metadata = self.metadata.get(file_key, {}).get("subsections", {})

            for section_name, section_data in note_data["subsections"].items():
                section_metadata = file_metadata.get(section_name, {})

                priority_score = self.calculate_study_priority(
                    section_data, section_metadata
                )

                all_sections.append(
                    {
                        "file": note_data["file_name"],
                        "file_path": str(file_path),
                        "main_topic": note_data["main_topic"],
                        "section": section_name,
                        "importance": section_data["importance"],
                        "priority_score": priority_score,
                        "key_terms_count": len(section_data["key_terms"]),
                        "content_lines": section_data["line_count"],
                        "last_reviewed": section_metadata.get("last_reviewed", "Never"),
                        "tags": note_data["tags"],
                    }
                )

        if debug:
            print(f"\nFiles processed: {files_processed}")
            print(f"Total sections found: {len(all_sections)}")

        if not all_sections:
            print("No sections found in notes!")
            if files_processed == 0:
                print("No .wiki files found!")
            else:
                print("Wiki files found but no parseable sections detected.")
                print("Make sure your files have the format:")
                print("= Main Topic =")
                print("== Subsection ==")
            return

        # Sort by priority or randomize
        if randomize:
            # Weighted randomization - higher importance more likely to be selected
            if focus_high_importance:
                high_sections = [s for s in all_sections if s["importance"] == "high"]
                medium_sections = [
                    s for s in all_sections if s["importance"] == "medium"
                ]
                low_sections = [s for s in all_sections if s["importance"] == "low"]

                # Select proportionally: 60% high, 30% medium, 10% low
                high_count = min(len(high_sections), int(target_sections * 0.6))
                medium_count = min(len(medium_sections), int(target_sections * 0.3))
                low_count = min(
                    len(low_sections), target_sections - high_count - medium_count
                )

                selected = []
                selected.extend(
                    random.sample(high_sections, high_count) if high_sections else []
                )
                selected.extend(
                    random.sample(medium_sections, medium_count)
                    if medium_sections
                    else []
                )
                selected.extend(
                    random.sample(low_sections, low_count) if low_sections else []
                )

                # Fill remaining spots if needed
                remaining = target_sections - len(selected)
                if remaining > 0:
                    unused = [s for s in all_sections if s not in selected]
                    selected.extend(random.sample(unused, min(remaining, len(unused))))

                study_sections = selected
            else:
                study_sections = random.sample(
                    all_sections, min(target_sections, len(all_sections))
                )
        else:
            # Sort by priority score
            all_sections.sort(key=lambda x: x["priority_score"], reverse=True)
            study_sections = all_sections[:target_sections]

        return study_sections

    def print_study_plan(self, study_sections, output_format="text", show_details=True):
        """Print the generated study plan"""
        today = datetime.now().strftime("%Y-%m-%d")

        if output_format == "wiki":
            print(f"% Note-Based Study Plan for {today}\n")
            print("== Today's Focus Areas ==")
        else:
            print(f"📚 Note-Based Study Plan - {today}")
            print("=" * 50)
            print("\n🎯 Today's Focus Areas:")

        for i, section in enumerate(study_sections, 1):
            importance_emoji = {"high": "🔥", "medium": "⚡", "low": "📝"}
            emoji = importance_emoji.get(section["importance"], "📝")

            if output_format == "wiki":
                print(
                    f"* [ ] {emoji} **{section['main_topic']}** - {section['section']}"
                )
                if show_details:
                    print(f"  - File: `{section['file']}`")
                    print(f"  - Priority Score: {section['priority_score']}")
                    print(f"  - Key Terms: {section['key_terms_count']}")
                    print(f"  - Last Reviewed: {section['last_reviewed']}")
                    if section["tags"]:
                        print(f"  - Tags: {', '.join(section['tags'])}")
            else:
                print(f"\n{i}. {emoji} {section['main_topic']} - {section['section']}")
                if show_details:
                    print(f"   📁 File: {section['file']}")
                    print(
                        f"   🎯 Priority: {section['priority_score']} ({section['importance']} importance)"
                    )
                    print(f"   🔑 Key Terms: {section['key_terms_count']}")
                    print(f"   📅 Last Reviewed: {section['last_reviewed']}")
                    if section["tags"]:
                        print(f"   🏷️  Tags: {', '.join(section['tags'])}")

        if output_format == "wiki":
            print(f"\n== Study Commands ==")
            print("Mark section complete:")
            for section in study_sections:
                print(
                    f"* `python note_planner.py --mark-reviewed \"{section['file']}\" \"{section['section']}\"`"
                )
        else:
            print(f"\n📝 Study Commands:")
            print("Mark sections as reviewed using:")
            for section in study_sections:
                print(
                    f"  python note_planner.py --mark-reviewed \"{section['file']}\" \"{section['section']}\""
                )

    def mark_section_reviewed(self, file_name, section_name):
        """Mark a specific section as reviewed"""
        if not file_name.endswith(".wiki"):
            file_name += ".wiki"

        today = datetime.now().strftime("%Y-%m-%d")

        if file_name not in self.metadata:
            self.metadata[file_name] = {"subsections": {}}

        if "subsections" not in self.metadata[file_name]:
            self.metadata[file_name]["subsections"] = {}

        if section_name not in self.metadata[file_name]["subsections"]:
            self.metadata[file_name]["subsections"][section_name] = {"review_count": 0}

        section_data = self.metadata[file_name]["subsections"][section_name]
        section_data["last_reviewed"] = today
        section_data["review_count"] = section_data.get("review_count", 0) + 1

        # Calculate next review date (spaced repetition)
        intervals = [1, 3, 7, 14, 30]
        interval_index = min(section_data["review_count"] - 1, len(intervals) - 1)
        next_review = datetime.now() + timedelta(days=intervals[interval_index])
        section_data["next_review"] = next_review.strftime("%Y-%m-%d")

        self._save_metadata()
        print(f"✅ Marked as reviewed: {file_name} - {section_name}")
        print(f"📅 Next review scheduled: {section_data['next_review']}")

    def show_statistics(self):
        """Show study statistics"""
        if not os.path.exists(self.notes_dir):
            print("No notes directory found!")
            return

        total_files = 0
        total_sections = 0
        importance_counts = {"high": 0, "medium": 0, "low": 0}
        reviewed_sections = 0

        for file_path in Path(self.notes_dir).rglob("*.wiki"):
            note_data = self.parse_note_file(file_path)
            total_files += 1

            for section_name, section_data in note_data["subsections"].items():
                total_sections += 1
                importance_counts[section_data["importance"]] += 1

                # Check if reviewed
                file_key = note_data["file_name"]
                if (
                    file_key in self.metadata
                    and "subsections" in self.metadata[file_key]
                    and section_name in self.metadata[file_key]["subsections"]
                ):
                    reviewed_sections += 1

        print("📊 Study Statistics")
        print("=" * 30)
        print(f"📁 Total Files: {total_files}")
        print(f"📚 Total Sections: {total_sections}")
        print(f"✅ Reviewed Sections: {reviewed_sections}")
        print(f"📋 Remaining: {total_sections - reviewed_sections}")
        print(f"\n🎯 By Importance:")
        print(f"  🔥 High: {importance_counts['high']}")
        print(f"  ⚡ Medium: {importance_counts['medium']}")
        print(f"  📝 Low: {importance_counts['low']}")

        if total_sections > 0:
            completion_rate = (reviewed_sections / total_sections) * 100
            print(f"\n📈 Completion Rate: {completion_rate:.1f}%")


def main():
    parser = argparse.ArgumentParser(description="Note-Based Study Planner")
    parser.add_argument(
        "--sections",
        type=int,
        default=5,
        help="Number of sections to study (default: 5)",
    )
    parser.add_argument("--wiki", action="store_true", help="Output in VimWiki format")
    parser.add_argument(
        "--randomize",
        action="store_true",
        help="Randomize selection (weighted by importance)",
    )
    parser.add_argument(
        "--no-focus-high",
        action="store_true",
        help="Don't prioritize high importance items",
    )
    parser.add_argument(
        "--mark-reviewed",
        nargs=2,
        metavar=("FILE", "SECTION"),
        help="Mark section as reviewed",
    )
    parser.add_argument("--stats", action="store_true", help="Show study statistics")
    parser.add_argument("--debug", action="store_true", help="Show debug information")
    parser.add_argument(
        "--notes-dir", default="notes/", help="Notes directory (default: notes/)"
    )

    args = parser.parse_args()

    planner = NoteStudyPlanner(notes_dir=args.notes_dir)

    if args.mark_reviewed:
        planner.mark_section_reviewed(args.mark_reviewed[0], args.mark_reviewed[1])
    elif args.stats:
        planner.show_statistics()
    else:
        focus_high = not args.no_focus_high
        study_sections = planner.generate_study_plan(
            target_sections=args.sections,
            focus_high_importance=focus_high,
            randomize=args.randomize,
            debug=args.debug,
        )

        if study_sections:
            output_format = "wiki" if args.wiki else "text"
            planner.print_study_plan(study_sections, output_format)
        else:
            print("No study sections generated. Check your notes directory!")


if __name__ == "__main__":
    main()
