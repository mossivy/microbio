#!/usr/bin/env python3
"""
Glossary Configuration Manager - Bulk update term metadata from YAML/JSON config
"""
import json
import yaml
import argparse
import sys
from pathlib import Path

# Add the scripts directory to Python path for importing
sys.path.insert(0, str(Path(__file__).parent))
from glossary_planner import GlossaryStudyPlanner


def load_config(config_file):
    """Load configuration from YAML or JSON file"""
    config_path = Path(config_file)

    # If relative path, resolve from parent directory (not scripts/)
    if not config_path.is_absolute():
        config_path = Path(__file__).parent.parent / config_file

    with open(config_path, "r") as f:
        if config_path.suffix.lower() in [".yaml", ".yml"]:
            return yaml.safe_load(f)
        else:
            return json.load(f)


def generate_sample_config(planner, output_file="glossary_config.yaml"):
    """Generate a sample configuration file with all terms"""
    if not planner.terms:
        planner.parse_glossary()

    # Group terms by chapter for better organization
    terms_by_chapter = {}
    unassigned_terms = {}

    for term_name, term_data in planner.terms.items():
        chapter = term_data.get("chapter")

        term_config = {
            "chapter": chapter or "",
            "exam_importance": term_data.get("exam_importance", "medium"),
            "study_importance": term_data.get("study_importance", "medium"),
            "tags": term_data.get("tags", []),
            "notes": "",  # Optional field for additional notes
        }

        if chapter:
            if chapter not in terms_by_chapter:
                terms_by_chapter[chapter] = {}
            terms_by_chapter[chapter][term_name] = term_config
        else:
            unassigned_terms[term_name] = term_config

    # Create organized config structure
    config = {
        "metadata_version": "1.0",
        "description": "Glossary term metadata configuration",
        "terms": {},
    }

    # Add terms organized by chapter
    for chapter in sorted(terms_by_chapter.keys(), key=lambda x: str(x)):
        chapter_comment = f"\n# Chapter {chapter} Terms\n"
        # We'll add this as a comment in the YAML output
        for term_name, term_config in sorted(terms_by_chapter[chapter].items()):
            config["terms"][term_name] = term_config

    # Add unassigned terms at the end
    if unassigned_terms:
        for term_name, term_config in sorted(unassigned_terms.items()):
            config["terms"][term_name] = term_config

    # Save to parent directory (not scripts/)
    output_path = Path(__file__).parent.parent / "config" / output_file

    # Save as YAML with custom formatting for better readability
    with open(output_path, "w") as f:
        f.write("# Glossary Term Metadata Configuration\n")
        f.write(
            "# This file controls chapter assignments, importance levels, and tags\n"
        )
        f.write("# for all glossary terms.\n\n")

        f.write(f"metadata_version: '{config['metadata_version']}'\n")
        f.write(f"description: {config['description']}\n\n")
        f.write("terms:\n")

        current_chapter = None
        for term_name in sorted(
            config["terms"].keys(),
            key=lambda x: (config["terms"][x].get("chapter") or "ZZZ", x),
        ):
            term_config = config["terms"][term_name]
            term_chapter = term_config.get("chapter")

            # Add chapter header comment
            if term_chapter != current_chapter:
                if term_chapter:
                    f.write(f"\n  # === Chapter {term_chapter} Terms ===\n")
                else:
                    f.write(f"\n  # === Unassigned Terms ===\n")
                current_chapter = term_chapter

            f.write(f"  {term_name}:\n")
            f.write(f"    chapter: {term_chapter or 'null'}\n")
            f.write(f"    exam_importance: {term_config['exam_importance']}\n")
            f.write(f"    study_importance: {term_config['study_importance']}\n")

            if term_config["tags"]:
                f.write(f"    tags: {term_config['tags']}\n")
            else:
                f.write(f"    tags: []\n")

            f.write(f"    notes: '{term_config['notes']}'\n")

    print(
        f"✅ Generated organized config with {len(config['terms'])} terms: {output_path}"
    )
    print("📋 Terms are organized by chapter for easy editing")
    print(
        "💡 Tip: The system auto-detected chapters and tags from your topics/ directory"
    )
    print("✏️  Edit this file to customize chapters, importance levels, and tags")


def apply_config(planner, config_file):
    """Apply configuration to glossary terms"""
    config = load_config(config_file)

    if not planner.terms:
        planner.parse_glossary()

    if "terms" not in config:
        print("❌ Config file must have 'terms' section")
        return

    updated_count = 0
    errors = []

    for term_name, term_config in config["terms"].items():
        if term_name not in planner.terms:
            errors.append(f"Term '{term_name}' not found in glossary")
            continue

        # Prepare updates
        updates = {}

        # Chapter
        if "chapter" in term_config and term_config["chapter"]:
            updates["chapter"] = term_config["chapter"]

        # Importance levels
        if "exam_importance" in term_config:
            if term_config["exam_importance"] in ["high", "medium", "low"]:
                updates["exam_importance"] = term_config["exam_importance"]
            else:
                errors.append(
                    f"Invalid exam_importance for '{term_name}': {term_config['exam_importance']}"
                )

        if "study_importance" in term_config:
            if term_config["study_importance"] in ["high", "medium", "low"]:
                updates["study_importance"] = term_config["study_importance"]
            else:
                errors.append(
                    f"Invalid study_importance for '{term_name}': {term_config['study_importance']}"
                )

        # Tags
        if "tags" in term_config and isinstance(term_config["tags"], list):
            updates["tags"] = term_config["tags"]

        # Apply updates
        if updates:
            planner.update_term_metadata(term_name, **updates)
            updated_count += 1

    print(f"\n✅ Updated {updated_count} terms")
    if errors:
        print(f"\n❌ Errors encountered:")
        for error in errors:
            print(f"  - {error}")


def main():
    parser = argparse.ArgumentParser(description="Manage glossary term metadata")
    parser.add_argument(
        "--glossary", default="glossary.wiki", help="Glossary file path"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Generate sample config
    gen_parser = subparsers.add_parser(
        "generate", help="Generate sample configuration file"
    )
    gen_parser.add_argument(
        "--output", default="glossary_config.yaml", help="Output file name"
    )

    # Apply config
    apply_parser = subparsers.add_parser("apply", help="Apply configuration to terms")
    apply_parser.add_argument("config_file", help="Configuration file to apply")

    # Validate config
    validate_parser = subparsers.add_parser(
        "validate", help="Validate configuration file"
    )
    validate_parser.add_argument("config_file", help="Configuration file to validate")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    planner = GlossaryStudyPlanner(glossary_file=args.glossary)

    if args.command == "generate":
        generate_sample_config(planner, args.output)
    elif args.command == "apply":
        apply_config(planner, args.config_file)
    elif args.command == "validate":
        try:
            config = load_config(args.config_file)
            planner.parse_glossary()

            errors = []
            warnings = []

            if "terms" not in config:
                errors.append("Missing 'terms' section in config")
            else:
                for term_name, term_config in config["terms"].items():
                    if term_name not in planner.terms:
                        warnings.append(f"Term '{term_name}' not found in glossary")

                    # Validate importance values
                    for importance_field in ["exam_importance", "study_importance"]:
                        if importance_field in term_config:
                            if term_config[importance_field] not in [
                                "high",
                                "medium",
                                "low",
                            ]:
                                errors.append(
                                    f"Invalid {importance_field} for '{term_name}': {term_config[importance_field]}"
                                )

            if errors:
                print("❌ Validation errors:")
                for error in errors:
                    print(f"  - {error}")

            if warnings:
                print("⚠️  Warnings:")
                for warning in warnings:
                    print(f"  - {warning}")

            if not errors and not warnings:
                print("✅ Configuration file is valid!")

        except Exception as e:
            print(f"❌ Failed to validate config: {e}")


if __name__ == "__main__":
    main()
