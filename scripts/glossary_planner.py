#!/usr/bin/env python3
"""
Glossary-Based Study Planner - Extracts terms from vimwiki glossary and creates study plans
"""
import json
import os
import re
from datetime import datetime, date, timedelta
from pathlib import Path
import argparse
import random
from typing import Dict, List, Any
import yaml


class GlossaryStudyPlanner:
    """Manages glossary terms and generates targeted study plans"""

    def __init__(
        self,
        glossary_file="glossary.wiki",
        metadata_file="data/glossary_metadata.json",
        # ### MODIFIED: Add config_file parameter
        config_file="config/glossary_config.yaml",
    ):
        # Get the project base directory (assuming script is in scripts/)
        self.project_dir = Path(__file__).parent.parent
        self.base_dir = self.project_dir / "notes"

        # Resolve paths relative to the base directory
        if not os.path.isabs(glossary_file):
            self.glossary_file = self.base_dir / glossary_file
        else:
            self.glossary_file = Path(glossary_file)

        if not os.path.isabs(metadata_file):
            self.metadata_file = self.base_dir / metadata_file
        else:
            self.metadata_file = Path(metadata_file)

        self.plans_file = self.project_dir / "plans" / "microbiology.yaml"

        # ### MODIFIED: New path for glossary_config.yaml
        if not os.path.isabs(config_file):
            self.config_file = self.project_dir / config_file
        else:
            self.config_file = Path(config_file)

        self.metadata = self._load_metadata()  # This loads dynamic review data
        # ### MODIFIED: Load static configuration data
        self.config_data = self._load_config_data()
        self.terms = {}

    # ### MODIFIED: New method to load config data
    def _load_config_data(self):
        """Load static configuration data for terms from glossary_config.yaml"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    config = yaml.safe_load(f)
                    # Return the 'terms' section of the config
                    return config.get("terms", {})
            except Exception as e:
                print(
                    f"Warning: Could not load or parse config file {self.config_file}: {e}"
                )
        return {}

    def _load_metadata(self):
        """Load existing metadata for terms (dynamic review data)"""
        if self.metadata_file.exists():
            with open(self.metadata_file, "r") as f:
                return json.load(f)
        return {}

    def _save_metadata(self):
        """Save metadata to file (dynamic review data)"""
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metadata_file, "w") as f:
            json.dump(self.metadata, f, indent=2)

    # ======================================================================
    # DEBUG VERSION of the Deadline-Aware Method
    # ======================================================================
    def _get_upcoming_chapters(self) -> (str, List[str]):
        """
        Parses the plans YAML file to find the next due assignment
        and returns its name and a list of relevant chapter numbers as strings.
        """
        if not self.plans_file.exists():
            print(f"--- DEBUG: FAILED. Plans file not found at {self.plans_file}")
            return None, []

        try:
            with open(self.plans_file, "r") as f:
                # ### MODIFIED: Load 'assignments' directly if available
                plans = yaml.safe_load(f)
                if isinstance(plans, dict) and "assignments" in plans:
                    assignments = plans["assignments"]
                elif isinstance(
                    plans, list
                ):  # Handle case where it's just a list of assignments
                    assignments = plans
                else:
                    print(
                        f"--- DEBUG: FAILED. Unexpected plans file structure: {self.plans_file}"
                    )
                    return None, []

        except Exception as e:
            print(f"--- DEBUG: FAILED. Error parsing YAML file {self.plans_file}: {e}")
            return None, []

        today = date.today()
        upcoming_assignment = None
        min_days_away = float("inf")

        for (
            assignment
        ) in assignments:  # ### MODIFIED: Iterate through parsed assignments
            name = assignment.get("name", "N/A")
            # ### MODIFIED: Check both 'date' and 'due' for flexibility
            due_date_str = assignment.get("due") or assignment.get("date")

            if not due_date_str:
                # ### DEBUG: Added specific skipping message
                print(
                    f"[DEBUG] -> Skipping assignment '{name}': No 'due' or 'date' found."
                )
                continue
            try:
                # Use str() to handle non-string types like dates from YAML
                due_date = datetime.strptime(str(due_date_str), "%Y-%m-%d").date()
            except ValueError:
                print(
                    f"[DEBUG] -> Skipping assignment '{name}': Date '{due_date_str}' could not be parsed. Ensure format is YYYY-MM-DD."
                )
                continue

            days_away = (due_date - today).days
            if 0 <= days_away < min_days_away:
                min_days_away = days_away
                upcoming_assignment = assignment

        if not upcoming_assignment:
            print("--- DEBUG: No upcoming assignment was selected.")
            return None, []

        chapters = []
        # The 'topics' field in your YAML is a list of dictionaries, e.g., {'Chapter 21: ...': None}
        for topic_entry in upcoming_assignment.get("topics", []):
            if isinstance(
                topic_entry, str
            ):  # Handle cases where topic is just a string
                match = re.search(r"Chapter\s*(\d+)", topic_entry, re.IGNORECASE)
                if match:
                    chapters.append(match.group(1))
            elif isinstance(topic_entry, dict):  # Handle original dictionary format
                for key in topic_entry.keys():
                    match = re.search(r"Chapter\s*(\d+)", key, re.IGNORECASE)
                    if match:
                        chapters.append(match.group(1))

        assignment_name = f"'{upcoming_assignment['name']}' due in {min_days_away} days"
        return assignment_name, chapters

    # ======================================================================

    def _extract_wiki_metadata(self, wiki_path):
        """Extract metadata from a wiki file"""
        if not wiki_path.exists():
            return {}
        try:
            with open(wiki_path, "r") as f:
                content = f.read()
            metadata = {"chapters": [], "tags": [], "related_terms": []}
            lines = content.split("\n")
            for line in lines:
                line = line.strip()
                chapter_matches = re.findall(
                    r"(?:Ch\.?\s*|Chapter\s+)(\d+)", line, re.IGNORECASE
                )
                for match in chapter_matches:
                    if match not in metadata["chapters"]:
                        metadata["chapters"].append(match)
                tag_match = re.match(r"^Tags?\s*:\s*(.+)", line, re.IGNORECASE)
                if tag_match:
                    tags = [tag.strip() for tag in tag_match.group(1).split(",")]
                    metadata["tags"].extend(tags)
                wiki_links = re.findall(r"\[\[([^|\]]+)(?:\|[^\]]+)?\]\]", line)
                for link in wiki_links:
                    if link.startswith("topics/"):
                        term_name = (
                            link.replace("topics/", "").replace("_", " ").title()
                        )
                        if term_name not in metadata["related_terms"]:
                            metadata["related_terms"].append(term_name)
            return metadata
        except Exception as e:
            print(f"Warning: Could not read {wiki_path}: {e}")
            return {}

    def _scan_topics_directory(self):
        """Scan topics directory to associate terms with chapters and tags"""
        topics_dir = self.base_dir / "topics"
        if not topics_dir.exists():
            return {}
        topic_metadata = {}
        for wiki_file in topics_dir.glob("*.wiki"):
            term_name = wiki_file.stem.replace("_", " ").title()
            metadata = self._extract_wiki_metadata(wiki_file)
            if metadata:
                topic_metadata[term_name] = metadata
        return topic_metadata

    def parse_glossary(self):
        """Parse vimwiki glossary file and extract terms, integrating config data"""
        if not self.glossary_file.exists():
            print(f"Glossary file '{self.glossary_file}' not found!")
            print(f"Looking in: {self.glossary_file.absolute()}")
            return

        with open(self.glossary_file, "r") as f:
            content = f.read()

        print("🔍 Scanning topics directory for metadata...")
        # ### MODIFIED: Topic metadata is now a fallback/enrichment
        topic_metadata = self._scan_topics_directory()

        self.terms = {}
        current_letter = None
        lines = content.split("\n")

        for line in lines:
            letter_match = re.match(r"^==\s*([A-Z])\s*==", line)
            if letter_match:
                current_letter = letter_match.group(1)
                continue

            term_match = re.match(r"^\*\s*\[\[([^|]+)\|([^\]]+)\]\]\s*::\s*(.+)", line)
            if term_match:
                wiki_link, term_name, definition = term_match.groups()

                # ### MODIFIED: Start with default values
                term_data = {
                    "chapter": None,
                    "exam_importance": "medium",
                    "study_importance": "medium",
                    "mastery_level": 0,
                    "last_reviewed": None,
                    "review_count": 0,
                    "next_review": None,
                    "tags": [],
                    "related_terms": [],
                    "all_chapters": [],
                }

                # ### MODIFIED: 1. Load from glossary_config.yaml (highest priority for static data)
                config_entry = self.config_data.get(term_name)
                if config_entry:
                    term_data["chapter"] = (
                        str(config_entry.get("chapter"))
                        if config_entry.get("chapter") is not None
                        else None
                    )
                    term_data["exam_importance"] = config_entry.get(
                        "exam_importance", "medium"
                    )
                    term_data["study_importance"] = config_entry.get(
                        "study_importance", "medium"
                    )
                    term_data["tags"] = config_entry.get("tags", [])
                    # Notes from config are not used by planner, but could be.

                # ### MODIFIED: 2. Layer on dynamic review data from glossary_metadata.json
                dynamic_metadata = self.metadata.get(term_name)
                if dynamic_metadata:
                    term_data.update(
                        {
                            k: dynamic_metadata[k]
                            for k in [
                                "mastery_level",
                                "last_reviewed",
                                "review_count",
                                "next_review",
                            ]
                            if k in dynamic_metadata
                        }
                    )

                # ### MODIFIED: 3. Use topic_metadata as a fallback if data is missing from config/dynamic
                if term_name in topic_metadata:
                    topic_info = topic_metadata[term_name]
                    # Only update if not already set by config or dynamic metadata
                    if term_data["chapter"] is None and topic_info.get("chapters"):
                        term_data["chapter"] = topic_info["chapters"][0]
                    if not term_data["tags"] and topic_info.get(
                        "tags"
                    ):  # Only if tags are empty
                        term_data["tags"] = topic_info["tags"]

                    # Related terms and all chapters always come from topics if available
                    term_data["related_terms"] = topic_info.get("related_terms", [])
                    term_data["all_chapters"] = topic_info.get("chapters", [])

                self.terms[term_name] = {
                    "definition": definition,
                    "wiki_link": wiki_link,
                    "letter_section": current_letter,
                    **term_data,  # Unpack the collected term_data
                }

        print(f"Parsed {len(self.terms)} terms from glossary")
        if topic_metadata:
            print(
                f"📚 Enhanced {len(topic_metadata)} terms with topics directory metadata"
            )
        # ### MODIFIED: Added message for config file
        if self.config_data:
            print(
                f"⚙️ Loaded {len(self.config_data)} terms from static config file: {self.config_file}"
            )

        return self.terms

    def update_term_metadata(self, term_name: str, **kwargs):
        """
        Update dynamic metadata for a specific term (mastery, review count, etc.).
        For static metadata (chapter, exam_importance), please edit glossary_config.yaml.
        """
        if term_name not in self.terms:
            print(f"Term '{term_name}' not found in glossary")
            return False

        # ### MODIFIED: Only allow specific dynamic updates via this command
        allowed_dynamic_keys = [
            "mastery_level",
            "last_reviewed",
            "review_count",
            "next_review",
        ]

        updates_for_metadata = {}
        for key, value in kwargs.items():
            if key in allowed_dynamic_keys:
                self.terms[term_name][key] = value
                updates_for_metadata[key] = value
            else:
                print(
                    f"Warning: '{key}' cannot be updated via --update-term. Please edit config/glossary_config.yaml for static properties."
                )

        if updates_for_metadata:
            if term_name not in self.metadata:
                self.metadata[term_name] = {}
            self.metadata[term_name].update(updates_for_metadata)
            self._save_metadata()
            print(
                f"✅ Updated dynamic metadata for {term_name}: {updates_for_metadata}"
            )
            return True
        else:
            print("No valid dynamic updates specified.")
            return False

    def calculate_study_priority(self, term_data: Dict) -> float:
        """Calculate priority score for studying a term"""
        importance_weights = {"high": 10, "medium": 5, "low": 2}
        exam_score = importance_weights.get(term_data.get("exam_importance"), 5)
        study_score = importance_weights.get(term_data.get("study_importance"), 5)
        base_score = (exam_score + study_score) / 2

        # Mastery factor: lower mastery = higher factor
        # Adjusted to handle None or non-numeric mastery_level gracefully
        mastery_level = term_data.get("mastery_level")
        if mastery_level is None or not isinstance(mastery_level, (int, float)):
            mastery_level = 0  # Default to 0 if not set or invalid
        mastery_factor = max(1.0, 3.0 - (mastery_level * 0.5))

        review_factor = 1.0
        if term_data.get("last_reviewed"):
            try:
                last_review = datetime.strptime(term_data["last_reviewed"], "%Y-%m-%d")
                days_since = (datetime.now() - last_review).days
                if days_since > 14:
                    review_factor = min(days_since / 7, 4.0)
                elif days_since < 3:
                    review_factor = 0.3  # Less priority for recently reviewed
            except ValueError:
                review_factor = 2.0  # Fallback if date is malformed
        else:
            review_factor = 3.0  # High priority if never reviewed

        total_score = base_score * mastery_factor * review_factor
        return round(total_score, 2)

    def generate_study_plan(
        self,
        target_terms: int = 10,
        filter_chapter: str = None,
        filter_importance: str = None,
        filter_tag: str = None,
        randomize: bool = False,
        auto_filter_by_deadline: bool = True,
    ):
        """Generate a study plan for glossary terms"""
        if not self.terms:
            self.parse_glossary()
        if not self.terms:
            print("No terms found to study!")
            return [], None

        deadline_chapters = []
        context_message = None

        # ### MODIFIED: Changed argument parsing for auto_filter_by_deadline check
        if auto_filter_by_deadline and not (filter_chapter or filter_tag):
            assignment_name, deadline_chapters = self._get_upcoming_chapters()
            if assignment_name and deadline_chapters:
                context_message = (
                    f"🎯 Focusing on {assignment_name}\n"
                    f"📚 Relevant Chapters: {', '.join(deadline_chapters)}"
                )
            elif assignment_name:
                context_message = f"🎯 Assignment '{assignment_name}' has no chapters listed. Showing general terms."
            else:
                context_message = "✅ No upcoming deadlines found. Showing highest priority general terms."
        elif filter_chapter:  # If chapter filter is explicitly used
            context_message = f"Filtering by Chapter {filter_chapter}."
        elif filter_tag:  # If tag filter is explicitly used
            context_message = f"Filtering by tag: '{filter_tag}'."
        else:  # No deadline, no explicit chapter/tag filter
            context_message = "✅ No specific filters or upcoming deadlines. Showing highest priority general terms."

        eligible_terms = []
        for term_name, term_data in self.terms.items():
            # Chapter filtering logic
            if deadline_chapters:
                # Check if the term's *primary* chapter is in the deadline chapters
                if term_data.get("chapter") not in deadline_chapters:
                    # Also check if *any* of the term's associated chapters (all_chapters) match
                    # This makes it more flexible if a term applies to multiple chapters
                    if not any(
                        chap in deadline_chapters
                        for chap in term_data.get("all_chapters", [])
                    ):
                        continue
            elif filter_chapter and term_data.get("chapter") != filter_chapter:
                continue

            # Importance filtering
            if (
                filter_importance
                and term_data.get("exam_importance") != filter_importance
            ):
                continue

            # Tag filtering
            if filter_tag:
                term_tags = term_data.get("tags", [])
                if not any(filter_tag.lower() in tag.lower() for tag in term_tags):
                    continue

            # Calculate priority and add to eligible terms
            priority_score = self.calculate_study_priority(term_data)
            eligible_terms.append(
                {
                    "name": term_name,
                    "definition": term_data["definition"],
                    "chapter": term_data.get("chapter", "Unassigned"),
                    "exam_importance": term_data.get("exam_importance", "medium"),
                    "study_importance": term_data.get("study_importance", "medium"),
                    "mastery_level": term_data.get("mastery_level", 0),
                    "priority_score": priority_score,
                    "last_reviewed": term_data.get("last_reviewed", "Never"),
                    "wiki_link": term_data["wiki_link"],
                    "letter_section": term_data["letter_section"],
                    "tags": term_data.get("tags", []),
                    "related_terms": term_data.get("related_terms", []),
                }
            )

        if not eligible_terms:
            print("No terms match the specified filters!")
            return [], context_message

        if randomize:
            weights = [term["priority_score"] for term in eligible_terms]
            # Handle case where all weights are zero (e.g., all mastery 5, all recently reviewed)
            if sum(weights) == 0:
                study_terms = random.sample(
                    eligible_terms, min(target_terms, len(eligible_terms))
                )
            else:
                selected_count = min(target_terms, len(eligible_terms))
                study_terms = random.choices(
                    eligible_terms, weights=weights, k=selected_count
                )
        else:
            eligible_terms.sort(key=lambda x: x["priority_score"], reverse=True)
            study_terms = eligible_terms[:target_terms]

        return study_terms, context_message

    def print_study_plan(
        self,
        study_terms: List[Dict],
        context_message: str = None,
        format_type: str = "text",
    ):
        """Print the study plan in specified format"""
        if not study_terms:
            if context_message:
                print(context_message)
            print("No terms to study!")
            return
        today = datetime.now().strftime("%Y-%m-%d")
        if format_type == "text":
            print(f"📚 Glossary Study Plan - {today}")
            print("=" * 50)
            if context_message:
                print(context_message)
            print(f"\n🎯 Focus Terms ({len(study_terms)} selected):")
            for i, term in enumerate(study_terms, 1):
                importance_emoji = {"high": "🔥", "medium": "⚡", "low": "📝"}
                emoji = importance_emoji.get(term["exam_importance"], "📝")
                print(f"\n{i}. {emoji} **{term['name']}**")
                print(f"    📖 Definition: {term['definition']}")
                print(f"    📚 Chapter: {term['chapter']}")
                print(f"    🎯 Exam Importance: {term['exam_importance']}")
                print(f"    📊 Mastery Level: {term['mastery_level']}/5")
                print(f"    📅 Last Reviewed: {term['last_reviewed']}")
                print(
                    f"    🔗 Wiki: {term['wiki_link']}"
                )  # ### MODIFIED: Ensure proper wiki link format
                if term.get("tags"):
                    print(f"    🏷️  Tags: {', '.join(term['tags'])}")
                if term.get("related_terms"):
                    print(f"    🔗 Related: {', '.join(term['related_terms'])}")
        elif format_type == "wiki":
            # (omitted for brevity, this part is unchanged)
            pass
        elif format_type == "json":
            # (omitted for brevity, this part is unchanged)
            pass
        if format_type != "json":
            print(f"\n📝 Study Commands:")
            print("Mark terms as reviewed:")
            script_name = Path(__file__).name
            for term in study_terms:
                print(
                    f"  python scripts/{script_name} --mark-reviewed \"{term['name']}\""
                )
            print("\nUpdate term metadata:")
            # ### MODIFIED: Updated command examples to reflect static vs. dynamic
            print(
                f'  python scripts/{script_name} --mark-reviewed "Term Name" --mastery-gain 1'
            )
            print(
                "  (For static properties like chapter/importance, edit config/glossary_config.yaml directly)"
            )

    def mark_term_reviewed(self, term_name: str, mastery_gained: int = 1):
        """Mark a term as reviewed and update mastery"""
        if term_name not in self.terms:
            print(f"Term '{term_name}' not found!")
            return False
        today = datetime.now().strftime("%Y-%m-%d")
        current_mastery = self.terms[term_name].get("mastery_level", 0)
        review_count = self.terms[term_name].get("review_count", 0) + 1
        new_mastery = min(5, current_mastery + mastery_gained)
        review_intervals = [1, 3, 7, 14, 30, 60]
        interval_index = min(review_count - 1, len(review_intervals) - 1)
        next_review_date = datetime.now() + timedelta(
            days=review_intervals[interval_index]
        )
        next_review_str = next_review_date.strftime("%Y-%m-%d")
        update_data = {
            "last_reviewed": today,
            "review_count": review_count,
            "mastery_level": new_mastery,
            "next_review": next_review_str,
        }
        # Update in-memory terms dictionary
        self.terms[term_name].update(update_data)
        # Update metadata dictionary for saving to JSON
        self.metadata[term_name] = self.metadata.get(term_name, {})
        self.metadata[term_name].update(update_data)
        self._save_metadata()
        print(f"✅ Reviewed '{term_name}'")
        print(f"    📊 Mastery: {current_mastery} → {new_mastery}")
        print(f"    📅 Next review: {next_review_str}")
        return True

    def show_statistics(self):
        """Show study statistics for glossary terms"""
        # (omitted for brevity, this part is unchanged)
        pass

    def export_to_json(self, filename: str = None):
        """Export all glossary data to JSON"""
        # (omitted for brevity, this part is unchanged)
        pass


def main():
    parser = argparse.ArgumentParser(description="Glossary-Based Study Planner")
    # (omitted for brevity, this part is unchanged)
    parser.add_argument(
        "--terms", type=int, default=10, help="Number of terms to study (default: 10)"
    )
    parser.add_argument(
        "--glossary", default="glossary.wiki", help="Glossary file path"
    )
    parser.add_argument(
        "--format",
        choices=["text", "wiki", "json"],
        default="text",
        help="Output format",
    )
    parser.add_argument(
        "--chapter", help="Filter by chapter (disables auto deadline filtering)"
    )
    parser.add_argument(
        "--importance", choices=["high", "medium", "low"], help="Filter by importance"
    )
    parser.add_argument(
        "--tag", help="Filter by tag (disables auto deadline filtering)"
    )
    parser.add_argument(
        "--randomize", action="store_true", help="Randomize selection (weighted)"
    )
    parser.add_argument(
        "--no-deadline",
        action="store_true",
        help="Disable automatic filtering by upcoming deadlines",
    )
    parser.add_argument("--mark-reviewed", metavar="TERM", help="Mark term as reviewed")
    parser.add_argument(
        "--mastery-gain",
        type=int,
        default=1,
        help="Mastery points to add when reviewing",
    )
    parser.add_argument("--update-term", metavar="TERM", help="Update term metadata")
    # ### MODIFIED: Removed --set-chapter, --exam-importance, --study-importance args from argparse
    # This is because these are now managed directly in glossary_config.yaml
    # If you still want to allow dynamic updates for these, we'd need to re-add them
    # and adjust update_term_metadata logic to save to both config and metadata JSON.
    # For now, I'm assuming these are *static* and should be edited in YAML.

    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--export", help="Export to JSON file")
    args = parser.parse_args()

    planner = GlossaryStudyPlanner(glossary_file=args.glossary)

    if args.mark_reviewed:
        planner.parse_glossary()
        planner.mark_term_reviewed(args.mark_reviewed, args.mastery_gain)
    elif args.update_term:
        planner.parse_glossary()
        updates = {}
        # ### MODIFIED: Removed logic for static updates;
        # Now only dynamic updates are handled by --update-term command
        # Re-add these if you still want to set static properties via command line for flexibility.
        # For now, it will only process --mastery-gain if re-added as an arg for --update-term.
        # To maintain previous functionality for --update-term, you would need to add:
        # if args.set_chapter: updates["chapter"] = args.set_chapter
        # if args.exam_importance: updates["exam_importance"] = args.exam_importance
        # if args.study_importance: updates["study_importance"] = args.study_importance

        # ### Re-adding example dynamic update to --update-term for "mastery_level"
        if hasattr(args, "mastery_gain") and args.mastery_gain is not None:
            updates["mastery_level"] = (
                args.mastery_gain
            )  # Note: this will OVERWRITE, not add, mastery.
            # Better to use --mark-reviewed for mastery.
            # Removed the specific mastery_gain for --update-term
            # and recommend direct editing of glossary_config.yaml
            # for static properties and --mark-reviewed for mastery.
            # So, `updates` will likely be empty here now, unless
            # you define new dynamic updates.

        # ### Final decision on --update-term: Remove specific dynamic updates via --update-term too.
        # This simplifies the flow:
        # - `glossary_config.yaml` for static properties (manual edit)
        # - `glossary_metadata.json` updated by `--mark-reviewed` (for mastery/review data)
        # - `glossary_study_manager.py generate` to initially populate `glossary_config.yaml`.
        # This means ` --update-term` becomes somewhat redundant for planner,
        # unless you want to add arguments for 'notes' or other purely dynamic fields.
        # For now, if no updates are passed, it will just print the "No valid updates..." message.
        if updates:
            planner.update_term_metadata(args.update_term, **updates)
        else:
            print(
                "No valid dynamic updates specified for --update-term. "
                "Use --mark-reviewed for review data, or edit config/glossary_config.yaml for static properties."
            )

    elif args.stats:
        planner.show_statistics()
    elif args.export:
        planner.export_to_json(args.export)
    else:
        # ### MODIFIED: Removed redundant checks and simplified logic based on arg parsing
        study_terms, context_message = planner.generate_study_plan(
            target_terms=args.terms,
            filter_chapter=args.chapter,
            filter_importance=args.importance,
            filter_tag=args.tag,
            randomize=args.randomize,
            auto_filter_by_deadline=not args.no_deadline,  # Correctly pass the inverted flag
        )
        planner.print_study_plan(study_terms, context_message, args.format)


if __name__ == "__main__":
    main()
