#!/usr/bin/env python3
"""
Glossary-Based Study Planner - Extracts terms from vimwiki glossary and creates study plans
"""
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import random
from typing import Dict, List, Any


class GlossaryStudyPlanner:
    """Manages glossary terms and generates targeted study plans"""

    def __init__(
        self, glossary_file="glossary.wiki", metadata_file="data/glossary_metadata.json"
    ):
        # Get the parent directory (assuming script is in scripts/ subdirectory)
        self.base_dir = Path(__file__).parent.parent / "notes"

        # Resolve paths relative to the base directory
        if not os.path.isabs(glossary_file):
            self.glossary_file = self.base_dir / glossary_file
        else:
            self.glossary_file = Path(glossary_file)

        if not os.path.isabs(metadata_file):
            self.metadata_file = self.base_dir / metadata_file
        else:
            self.metadata_file = Path(metadata_file)

        self.metadata = self._load_metadata()
        self.terms = {}

    def _load_metadata(self):
        """Load existing metadata for terms"""
        if self.metadata_file.exists():
            with open(self.metadata_file, "r") as f:
                return json.load(f)
        return {}

    def _save_metadata(self):
        """Save metadata to file"""
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metadata_file, "w") as f:
            json.dump(self.metadata, f, indent=2)

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

                # Look for chapter references: Ch. 5, Chapter 8, etc.
                chapter_matches = re.findall(
                    r"(?:Ch\.?\s*|Chapter\s+)(\d+)", line, re.IGNORECASE
                )
                for match in chapter_matches:
                    if match not in metadata["chapters"]:
                        metadata["chapters"].append(match)

                # Look for tags in format: Tags: tag1, tag2, tag3
                tag_match = re.match(r"^Tags?\s*:\s*(.+)", line, re.IGNORECASE)
                if tag_match:
                    tags = [tag.strip() for tag in tag_match.group(1).split(",")]
                    metadata["tags"].extend(tags)

                # Look for wiki links to other terms
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
            # Convert filename to term name (e.g., peptide_bond.wiki -> Peptide Bond)
            term_name = wiki_file.stem.replace("_", " ").title()

            # Extract metadata from the wiki file
            metadata = self._extract_wiki_metadata(wiki_file)

            if metadata:
                topic_metadata[term_name] = metadata

        return topic_metadata

    def parse_glossary(self):
        """Parse vimwiki glossary file and extract terms"""
        if not self.glossary_file.exists():
            print(f"Glossary file '{self.glossary_file}' not found!")
            print(f"Looking in: {self.glossary_file.absolute()}")
            return

        with open(self.glossary_file, "r") as f:
            content = f.read()

        # Scan topics directory for additional metadata
        print("🔍 Scanning topics directory for metadata...")
        topic_metadata = self._scan_topics_directory()

        self.terms = {}
        current_letter = None
        lines = content.split("\n")

        for line in lines:
            # Check for letter sections (== E ==)
            letter_match = re.match(r"^==\s*([A-Z])\s*==", line)
            if letter_match:
                current_letter = letter_match.group(1)
                continue

            # Parse term lines with wiki links and definitions
            # Format: * [[topics/enzyme|Enzyme]] :: Definition here
            term_match = re.match(r"^\*\s*\[\[([^|]+)\|([^\]]+)\]\]\s*::\s*(.+)", line)
            if term_match:
                wiki_link = term_match.group(1)
                term_name = term_match.group(2)
                definition = term_match.group(3)

                # Get existing metadata or create defaults
                term_data = self.metadata.get(
                    term_name,
                    {
                        "chapter": None,
                        "exam_importance": "medium",
                        "study_importance": "medium",
                        "mastery_level": 0,
                        "last_reviewed": None,
                        "review_count": 0,
                        "next_review": None,
                        "tags": [],
                    },
                )

                # Enhance with topics directory metadata
                if term_name in topic_metadata:
                    topic_info = topic_metadata[term_name]

                    # Set chapter if not already set and we found one
                    if not term_data["chapter"] and topic_info["chapters"]:
                        term_data["chapter"] = topic_info["chapters"][
                            0
                        ]  # Use first chapter found

                    # Add tags if not already set
                    if not term_data["tags"] and topic_info["tags"]:
                        term_data["tags"] = topic_info["tags"]

                    # Store additional metadata
                    term_data["related_terms"] = topic_info.get("related_terms", [])
                    term_data["all_chapters"] = topic_info.get("chapters", [])

                self.terms[term_name] = {
                    "definition": definition,
                    "wiki_link": wiki_link,
                    "letter_section": current_letter,
                    **term_data,
                }

        print(f"Parsed {len(self.terms)} terms from glossary")
        if topic_metadata:
            print(
                f"📚 Enhanced {len(topic_metadata)} terms with topics directory metadata"
            )
        return self.terms

    def update_term_metadata(self, term_name: str, **kwargs):
        """Update metadata for a specific term"""
        if term_name not in self.terms:
            print(f"Term '{term_name}' not found in glossary")
            return False

        # Update the term data
        for key, value in kwargs.items():
            if key in [
                "chapter",
                "exam_importance",
                "study_importance",
                "mastery_level",
                "tags",
            ]:
                self.terms[term_name][key] = value

        # Update metadata storage
        if term_name not in self.metadata:
            self.metadata[term_name] = {}
        self.metadata[term_name].update(kwargs)
        self._save_metadata()
        print(f"✅ Updated {term_name}: {kwargs}")
        return True

    def calculate_study_priority(self, term_data: Dict) -> float:
        """Calculate priority score for studying a term"""
        importance_weights = {"high": 10, "medium": 5, "low": 2}

        # Base score from exam importance
        exam_score = importance_weights.get(term_data["exam_importance"], 5)
        study_score = importance_weights.get(term_data["study_importance"], 5)
        base_score = (exam_score + study_score) / 2

        # Mastery level factor (lower mastery = higher priority)
        mastery_factor = max(1.0, 3.0 - (term_data["mastery_level"] * 0.5))

        # Review history factor
        review_factor = 1.0
        if term_data["last_reviewed"]:
            try:
                last_review = datetime.strptime(term_data["last_reviewed"], "%Y-%m-%d")
                days_since = (datetime.now() - last_review).days
                if days_since > 14:
                    review_factor = min(days_since / 7, 4.0)
                elif days_since < 3:
                    review_factor = 0.3  # Recently reviewed, lower priority
            except ValueError:
                review_factor = 2.0
        else:
            review_factor = 3.0  # Never reviewed = high priority

        total_score = base_score * mastery_factor * review_factor
        return round(total_score, 2)

    def generate_study_plan(
        self,
        target_terms: int = 10,
        filter_chapter: str = None,
        filter_importance: str = None,
        filter_tag: str = None,
        randomize: bool = False,
    ):
        """Generate a study plan for glossary terms"""
        if not self.terms:
            self.parse_glossary()

        if not self.terms:
            print("No terms found to study!")
            return []

        # Filter terms
        eligible_terms = []
        for term_name, term_data in self.terms.items():
            # Chapter filter
            if filter_chapter and term_data.get("chapter") != filter_chapter:
                continue

            # Importance filter
            if (
                filter_importance
                and term_data.get("exam_importance") != filter_importance
            ):
                continue

            # Tag filter
            if filter_tag:
                term_tags = term_data.get("tags", [])
                if not any(filter_tag.lower() in tag.lower() for tag in term_tags):
                    continue

            priority_score = self.calculate_study_priority(term_data)
            eligible_terms.append(
                {
                    "name": term_name,
                    "definition": term_data["definition"],
                    "chapter": term_data.get("chapter", "Unassigned"),
                    "exam_importance": term_data["exam_importance"],
                    "study_importance": term_data["study_importance"],
                    "mastery_level": term_data["mastery_level"],
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
            return []

        # Sort or randomize selection
        if randomize:
            # Weighted random selection based on priority
            weights = [term["priority_score"] for term in eligible_terms]
            selected_count = min(target_terms, len(eligible_terms))
            selected_indices = random.choices(
                range(len(eligible_terms)), weights=weights, k=selected_count
            )
            study_terms = [eligible_terms[i] for i in selected_indices]
        else:
            # Sort by priority score
            eligible_terms.sort(key=lambda x: x["priority_score"], reverse=True)
            study_terms = eligible_terms[:target_terms]

        return study_terms

    def print_study_plan(self, study_terms: List[Dict], format_type: str = "text"):
        """Print the study plan in specified format"""
        if not study_terms:
            print("No terms to study!")
            return

        today = datetime.now().strftime("%Y-%m-%d")

        if format_type == "wiki":
            print(f"% Glossary Study Plan - {today}\n")
            print("== Terms to Study ==")
            for i, term in enumerate(study_terms, 1):
                print(f"* [ ] **{term['name']}** (Ch. {term['chapter']})")
                print(f"  - Definition: {term['definition']}")
                print(
                    f"  - Importance: {term['exam_importance']} | Mastery: {term['mastery_level']}/5"
                )
                print(f"  - Last Reviewed: {term['last_reviewed']}")
                print()
        elif format_type == "json":
            print(json.dumps(study_terms, indent=2))
        else:  # text format
            print(f"📚 Glossary Study Plan - {today}")
            print("=" * 50)
            print(f"\n🎯 Focus Terms ({len(study_terms)} selected):")
            for i, term in enumerate(study_terms, 1):
                importance_emoji = {"high": "🔥", "medium": "⚡", "low": "📝"}
                emoji = importance_emoji.get(term["exam_importance"], "📝")
                print(f"\n{i}. {emoji} **{term['name']}**")
                print(f"   📖 Definition: {term['definition']}")
                print(f"   📚 Chapter: {term['chapter']}")
                print(f"   🎯 Exam Importance: {term['exam_importance']}")
                print(f"   📊 Mastery Level: {term['mastery_level']}/5")
                print(f"   📅 Last Reviewed: {term['last_reviewed']}")
                print(f"   🔗 Wiki: {term['wiki_link']}")
                if term.get("tags"):
                    print(f"   🏷️  Tags: {', '.join(term['tags'])}")
                if term.get("related_terms"):
                    print(f"   🔗 Related: {', '.join(term['related_terms'])}")

        # Print study commands
        print(f"\n📝 Study Commands:")
        print("Mark terms as reviewed:")
        for term in study_terms:
            print(
                f"  python scripts/glossary_planner.py --mark-reviewed \"{term['name']}\""
            )
        print("\nUpdate term metadata:")
        print(
            '  python scripts/glossary_planner.py --update-term "Term Name" --chapter 5 --exam-importance high'
        )

    def mark_term_reviewed(self, term_name: str, mastery_gained: int = 1):
        """Mark a term as reviewed and update mastery"""
        if term_name not in self.terms:
            print(f"Term '{term_name}' not found!")
            return False

        today = datetime.now().strftime("%Y-%m-%d")

        # Update term data
        self.terms[term_name]["last_reviewed"] = today
        self.terms[term_name]["review_count"] = (
            self.terms[term_name].get("review_count", 0) + 1
        )

        # Update mastery level (cap at 5)
        current_mastery = self.terms[term_name]["mastery_level"]
        new_mastery = min(5, current_mastery + mastery_gained)
        self.terms[term_name]["mastery_level"] = new_mastery

        # Calculate next review date (spaced repetition)
        review_intervals = [1, 3, 7, 14, 30, 60]  # days
        review_count = self.terms[term_name]["review_count"]
        interval_index = min(review_count - 1, len(review_intervals) - 1)
        next_review = datetime.now() + timedelta(days=review_intervals[interval_index])
        self.terms[term_name]["next_review"] = next_review.strftime("%Y-%m-%d")

        # Update metadata
        self.metadata[term_name] = self.metadata.get(term_name, {})
        self.metadata[term_name].update(
            {
                "last_reviewed": today,
                "review_count": self.terms[term_name]["review_count"],
                "mastery_level": new_mastery,
                "next_review": self.terms[term_name]["next_review"],
            }
        )
        self._save_metadata()

        print(f"✅ Reviewed '{term_name}'")
        print(f"   📊 Mastery: {current_mastery} → {new_mastery}")
        print(f"   📅 Next review: {self.terms[term_name]['next_review']}")
        return True

    def show_statistics(self):
        """Show study statistics for glossary terms"""
        if not self.terms:
            self.parse_glossary()

        total_terms = len(self.terms)
        if total_terms == 0:
            print("No terms found!")
            return

        # Count by importance
        importance_counts = {"high": 0, "medium": 0, "low": 0, "unset": 0}
        mastery_levels = [0, 0, 0, 0, 0, 0]  # 0-5 mastery levels
        reviewed_count = 0
        chapter_counts = {}
        tag_counts = {}

        for term_data in self.terms.values():
            # Importance
            importance = term_data.get("exam_importance", "unset")
            importance_counts[importance] = importance_counts.get(importance, 0) + 1

            # Mastery
            mastery = term_data.get("mastery_level", 0)
            mastery_levels[mastery] += 1

            # Reviewed
            if term_data.get("last_reviewed"):
                reviewed_count += 1

            # Chapters
            chapter = term_data.get("chapter", "Unassigned")
            chapter_counts[chapter] = chapter_counts.get(chapter, 0) + 1

            # Tags
            tags = term_data.get("tags", [])
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        print("📊 Glossary Study Statistics")
        print("=" * 40)
        print(f"📚 Total Terms: {total_terms}")
        print(f"✅ Reviewed Terms: {reviewed_count}")
        print(f"📋 Never Reviewed: {total_terms - reviewed_count}")

        print(f"\n🎯 By Exam Importance:")
        for importance, count in importance_counts.items():
            emoji = {"high": "🔥", "medium": "⚡", "low": "📝", "unset": "❓"}.get(
                importance, "❓"
            )
            print(f"  {emoji} {importance.title()}: {count}")

        print(f"\n📊 By Mastery Level:")
        for level, count in enumerate(mastery_levels):
            if count > 0:
                print(f"  Level {level}: {count} terms")

        print(f"\n📚 By Chapter:")
        for chapter, count in sorted(chapter_counts.items()):
            print(f"  {chapter}: {count} terms")

        if tag_counts:
            print(f"\n🏷️  By Tags:")
            for tag, count in sorted(
                tag_counts.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {tag}: {count} terms")

        if total_terms > 0:
            avg_mastery = (
                sum(
                    term_data.get("mastery_level", 0)
                    for term_data in self.terms.values()
                )
                / total_terms
            )
            completion_rate = (reviewed_count / total_terms) * 100
            print(f"\n📈 Average Mastery: {avg_mastery:.1f}/5")
            print(f"📈 Review Completion: {completion_rate:.1f}%")

    def export_to_json(self, filename: str = None):
        """Export all glossary data to JSON"""
        if not self.terms:
            self.parse_glossary()

        if not filename:
            filename = (
                f"glossary_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        # Save exports to the base directory
        export_path = self.base_dir / filename

        export_data = {
            "exported_date": datetime.now().isoformat(),
            "total_terms": len(self.terms),
            "terms": self.terms,
        }

        with open(export_path, "w") as f:
            json.dump(export_data, f, indent=2)

        print(f"✅ Exported {len(self.terms)} terms to {export_path}")


def main():
    parser = argparse.ArgumentParser(description="Glossary-Based Study Planner")

    # Basic options
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

    # Filtering options
    parser.add_argument("--chapter", help="Filter by chapter")
    parser.add_argument(
        "--importance", choices=["high", "medium", "low"], help="Filter by importance"
    )
    parser.add_argument("--tag", help="Filter by tag")
    parser.add_argument(
        "--randomize", action="store_true", help="Randomize selection (weighted)"
    )

    # Actions
    parser.add_argument("--mark-reviewed", metavar="TERM", help="Mark term as reviewed")
    parser.add_argument(
        "--mastery-gain",
        type=int,
        default=1,
        help="Mastery points to add when reviewing",
    )

    # Term management
    parser.add_argument("--update-term", metavar="TERM", help="Update term metadata")
    parser.add_argument("--set-chapter", type=str, help="Set chapter for term")
    parser.add_argument(
        "--exam-importance",
        choices=["high", "medium", "low"],
        help="Set exam importance",
    )
    parser.add_argument(
        "--study-importance",
        choices=["high", "medium", "low"],
        help="Set study importance",
    )

    # Utilities
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
        if args.set_chapter:
            updates["chapter"] = args.set_chapter
        if args.exam_importance:
            updates["exam_importance"] = args.exam_importance
        if args.study_importance:
            updates["study_importance"] = args.study_importance

        if updates:
            planner.update_term_metadata(args.update_term, **updates)
        else:
            print(
                "No updates specified. Use --set-chapter, --exam-importance, or --study-importance"
            )
    elif args.stats:
        planner.show_statistics()
    elif args.export:
        planner.export_to_json(args.export)
    else:
        # Generate study plan
        study_terms = planner.generate_study_plan(
            target_terms=args.terms,
            filter_chapter=args.chapter,
            filter_importance=args.importance,
            filter_tag=args.tag,
            randomize=args.randomize,
        )

        if study_terms:
            planner.print_study_plan(study_terms, args.format)
        else:
            print("No terms selected for study plan!")


if __name__ == "__main__":
    main()
