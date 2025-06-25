#!/usr/bin/env python3
"""
Enhanced Study Suite - Integrates assignment tracking with vimwiki notes and spaced repetition
"""

import yaml
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
import argparse


class StudyMetadata:
    """Manages study progress and review scheduling"""

    def __init__(self, metadata_file="data/study_metadata.json"):
        self.metadata_file = metadata_file
        self.data = self._load_metadata()

    def _load_metadata(self):
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, "r") as f:
                return json.load(f)
        return {}

    def save_metadata(self):
        os.makedirs(os.path.dirname(self.metadata_file), exist_ok=True)
        with open(self.metadata_file, "w") as f:
            json.dump(self.data, f, indent=2)

    def mark_reviewed(self, file_path, section=None):
        """Mark a topic or section as reviewed and calculate next review date"""
        file_key = os.path.basename(file_path)
        today = datetime.now().strftime("%Y-%m-%d")

        if file_key not in self.data:
            self.data[file_key] = {"subsections": {}}

        if section:
            # Mark specific subsection
            if section not in self.data[file_key]["subsections"]:
                self.data[file_key]["subsections"][section] = {"review_count": 0}

            section_data = self.data[file_key]["subsections"][section]
            section_data["last_reviewed"] = today
            section_data["review_count"] += 1

            # Spaced repetition intervals: 1, 3, 7, 14, 30 days
            intervals = [1, 3, 7, 14, 30]
            interval_index = min(section_data["review_count"] - 1, len(intervals) - 1)
            next_review = datetime.now() + timedelta(days=intervals[interval_index])
            section_data["next_review"] = next_review.strftime("%Y-%m-%d")
        else:
            # Mark entire topic
            self.data[file_key]["topic_last_reviewed"] = today
            next_review = datetime.now() + timedelta(
                days=7
            )  # Default 7 days for topics
            self.data[file_key]["topic_next_review"] = next_review.strftime("%Y-%m-%d")

        self.save_metadata()


class VimwikiParser:
    """Parses vimwiki files to extract topics, subsections, and importance levels"""

    def __init__(self, notes_dir="notes/"):
        self.notes_dir = notes_dir

    def parse_file(self, file_path):
        """Parse a vimwiki file and extract structure"""
        with open(file_path, "r") as f:
            content = f.read()

        result = {
            "file_path": file_path,
            "topics": [],
            "subsections": {},
            "tags": [],
            "importance": "medium",  # default
        }

        lines = content.split("\n")
        current_section = None

        for line in lines:
            # Extract main topic (= Topic =)
            topic_match = re.match(r"^=\s*(.+?)\s*=$", line)
            if topic_match:
                topic_name = topic_match.group(1)
                result["topics"].append(topic_name)

                # Check for importance and tags in surrounding lines
                continue

            # Extract subsections (== Section ==)
            section_match = re.match(r"^==\s*(.+?)\s*==$", line)
            if section_match:
                current_section = section_match.group(1)
                result["subsections"][current_section] = {
                    "importance": "medium",  # default
                    "content_lines": [],
                }

                # Check for importance tag
                importance_match = re.search(r"\[importance:\s*(\w+)\]", line)
                if importance_match:
                    result["subsections"][current_section]["importance"] = (
                        importance_match.group(1)
                    )
                continue

            # Extract tags
            if line.startswith("tags:"):
                tags = [tag.strip() for tag in line.replace("tags:", "").split(",")]
                result["tags"] = tags
                continue

            # Extract importance
            if line.startswith("importance:"):
                result["importance"] = line.replace("importance:", "").strip()
                continue

            # Add content to current section
            if current_section and line.strip():
                result["subsections"][current_section]["content_lines"].append(line)

        return result

    def get_all_notes(self):
        """Get all vimwiki files and parse them"""
        notes = []
        if not os.path.exists(self.notes_dir):
            return notes

        for file_path in Path(self.notes_dir).glob("*.wiki"):
            notes.append(self.parse_file(file_path))

        return notes


class StudyPlanner:
    """Enhanced study planner that combines assignments with note review"""

    def __init__(self, notes_dir="notes/", metadata_file="data/study_metadata.json"):
        self.parser = VimwikiParser(notes_dir)
        self.metadata = StudyMetadata(metadata_file)

    def get_due_for_review(self):
        """Get topics/sections that are due for review based on spaced repetition"""
        today = datetime.now().date()
        due_items = []

        notes = self.parser.get_all_notes()

        for note in notes:
            file_key = os.path.basename(note["file_path"])

            # Check if we have metadata for this file
            if file_key not in self.metadata.data:
                # New file - add all subsections as due for first review
                for section_name in note["subsections"]:
                    due_items.append(
                        {
                            "file": file_key,
                            "section": section_name,
                            "importance": note["subsections"][section_name][
                                "importance"
                            ],
                            "type": "new",
                            "days_overdue": 0,
                        }
                    )
                continue

            file_data = self.metadata.data[file_key]

            # Check subsections
            for section_name, section_info in note["subsections"].items():
                if section_name in file_data["subsections"]:
                    section_data = file_data["subsections"][section_name]
                    if "next_review" in section_data:
                        next_review = datetime.strptime(
                            section_data["next_review"], "%Y-%m-%d"
                        ).date()
                        if next_review <= today:
                            days_overdue = (today - next_review).days
                            due_items.append(
                                {
                                    "file": file_key,
                                    "section": section_name,
                                    "importance": section_info["importance"],
                                    "type": "review",
                                    "days_overdue": days_overdue,
                                }
                            )
                else:
                    # New section in existing file
                    due_items.append(
                        {
                            "file": file_key,
                            "section": section_name,
                            "importance": section_info["importance"],
                            "type": "new",
                            "days_overdue": 0,
                        }
                    )

        # Sort by importance and days overdue
        importance_weight = {"high": 3, "medium": 2, "low": 1}
        due_items.sort(
            key=lambda x: (
                importance_weight.get(x["importance"], 2),
                x["days_overdue"],
            ),
            reverse=True,
        )

        return due_items

    def generate_integrated_plan(self, assignment_file, output_format="text"):
        """Generate plan that combines assignments with review schedule"""

        # Get assignment plan (your existing logic)
        with open(assignment_file, "r") as f:
            plan = yaml.safe_load(f)

        today = datetime.now()
        today_date = today.date()

        # Get today's assignments
        todays_assignments = [
            a
            for a in plan.get("assignments", [])
            if datetime.strptime(a["date"], "%Y-%m-%d").date() == today_date
        ]

        # Get upcoming assignments (next 5 days)
        upcoming_assignments = sorted(
            [
                a
                for a in plan.get("assignments", [])
                if 0
                < (datetime.strptime(a["date"], "%Y-%m-%d").date() - today_date).days
                <= 5
            ],
            key=lambda x: datetime.strptime(x["date"], "%Y-%m-%d"),
        )

        # Get review items
        review_items = self.get_due_for_review()

        # Generate output
        if output_format == "wiki":
            print(f"% {plan['course']} Study Plan for {today.strftime('%Y-%m-%d')}\n")
        else:
            print(f"Study Plan for {plan['course']} - {today.strftime('%Y-%m-%d')}")
            print("=" * 50)

        # Today's urgent items
        if todays_assignments:
            self._print_section(
                "URGENT: DUE TODAY!", todays_assignments, output_format, today_date
            )

        # Upcoming assignments
        if upcoming_assignments:
            self._print_section(
                "Upcoming This Week", upcoming_assignments, output_format, today_date
            )

        # Review items
        if review_items:
            header = f"Review Schedule ({len(review_items)} items due)"
            if output_format == "wiki":
                print(f"== {header} ==")
            else:
                print(f"\n- {header} -")

            for item in review_items[:10]:  # Show top 10
                status = (
                    "NEW"
                    if item["type"] == "new"
                    else f"{item['days_overdue']}d overdue"
                )
                importance_marker = (
                    "🔥"
                    if item["importance"] == "high"
                    else "⚡" if item["importance"] == "medium" else "📝"
                )

                if output_format == "wiki":
                    print(
                        f"* [ ] {importance_marker} {item['file']} - {item['section']} ({status})"
                    )
                else:
                    print(
                        f"  {importance_marker} {item['file']} - {item['section']} ({status})"
                    )

        if not todays_assignments and not upcoming_assignments and not review_items:
            print("Nothing on the schedule. Take a well-deserved break!")

    def _print_section(self, header, assignments, output_format, today_date):
        """Helper to print assignment sections"""
        if output_format == "wiki":
            print(f"== {header} ==")
        else:
            print(f"\n- {header} -")

        for assignment in assignments:
            due_date = datetime.strptime(assignment["date"], "%Y-%m-%d").date()
            days_left = (due_date - today_date).days

            if output_format == "wiki":
                print(
                    f"* *{assignment['name']}* - Due in {days_left} day(s) ({assignment['date']})"
                )
                if assignment.get("location"):
                    print(f"  Location: {assignment['location']}")
                topics = self._parse_topics(assignment.get("topics", []))
                if topics:
                    for topic in topics:
                        print(f"  - [ ] {topic}")
            else:
                print(
                    f"\n*{assignment['name']}* (Due in {days_left} days - {assignment['date']})"
                )
                if assignment.get("location"):
                    print(f"  Location: {assignment['location']}")
                topics = self._parse_topics(assignment.get("topics", []))
                if topics:
                    print("  Topics:")
                    for topic in topics:
                        print(f"    - {topic}")

    def _parse_topics(self, topics_list):
        """Parse topics from assignment (your existing logic)"""
        parsed = []
        for topic in topics_list:
            if "&" in topic:
                parsed.extend(
                    [
                        f"Chapter {t.strip()}"
                        for t in topic.replace("Chapter", "").split("&")
                    ]
                )
            else:
                parsed.append(topic)
        return parsed

    def mark_completed(self, file_name, section_name=None):
        """Mark a study session as completed"""
        file_path = (
            f"notes/{file_name}"
            if not file_name.endswith(".wiki")
            else f"notes/{file_name}"
        )
        self.metadata.mark_reviewed(file_path, section_name)
        print(
            f"✅ Marked as reviewed: {file_name}"
            + (f" - {section_name}" if section_name else "")
        )


def main():
    parser = argparse.ArgumentParser(description="Enhanced Study Suite")
    parser.add_argument("--wiki", action="store_true", help="Output in VimWiki format")
    parser.add_argument(
        "--plan-file", default="plans/microbiology.yaml", help="Assignment plan file"
    )
    parser.add_argument(
        "--mark-reviewed", nargs="+", help="Mark topic as reviewed: filename [section]"
    )
    parser.add_argument("--status", action="store_true", help="Show review status")

    args = parser.parse_args()

    planner = StudyPlanner()

    if args.mark_reviewed:
        file_name = args.mark_reviewed[0]
        section_name = args.mark_reviewed[1] if len(args.mark_reviewed) > 1 else None
        planner.mark_completed(file_name, section_name)
    elif args.status:
        review_items = planner.get_due_for_review()
        print(f"Items due for review: {len(review_items)}")
        for item in review_items[:5]:
            print(f"  - {item['file']} - {item['section']} ({item['importance']})")
    else:
        output_format = "wiki" if args.wiki else "text"
        planner.generate_integrated_plan(args.plan_file, output_format)


if __name__ == "__main__":
    main()
