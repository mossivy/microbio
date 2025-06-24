import yaml
from datetime import datetime
import argparse


# --- Helper function to parse topics ---
def parse_topics(topics_list):
    # This ensures each topic is a single line item
    parsed = []
    for topic in topics_list:
        # Split topics that might have been combined, e.g., "Chapters 1&3"
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


# --- Main Generator Logic ---
def generate_study_plan(plan_file, output_format="text"):
    with open(plan_file, "r") as f:
        plan = yaml.safe_load(f)

    today = datetime.now()
    today_date = today.date()  # Get just the date part for accurate day calculations

    # Get today's assignments
    todays_assignments = [
        a
        for a in plan.get("assignments", [])
        if datetime.strptime(a["date"], "%Y-%m-%d").date() == today_date
    ]

    # Get upcoming assignments
    upcoming_assignments = sorted(
        [
            a
            for a in plan.get("assignments", [])
            if datetime.strptime(a["date"], "%Y-%m-%d").date() > today_date
        ],
        key=lambda x: datetime.strptime(x["date"], "%Y-%m-%d"),
    )

    # --- Generate Output ---
    if output_format == "wiki":
        print(f"% {plan['course']} Study Plan for {today.strftime('%Y-%m-%d')}\n")
    else:
        print(f"Study Plan for {plan['course']} - {today.strftime('%Y-%m-%d')}")
        print("=" * 40)

    # --- Today's Deadlines ---
    if todays_assignments:
        header = "URGENT: DUE TODAY!"
        if output_format == "wiki":
            print(f"== {header} ==")
        else:
            print(f"\n- {header} -")

        for assignment in todays_assignments:
            item = f"**{assignment['name']}**"
            if assignment.get("location"):
                item += f" at {assignment['location']}"
            if output_format == "wiki":
                print(f"* {item}")
            else:
                print(item)

            # Show study topics for today's assignments
            if assignment.get("topics"):
                topics = parse_topics(assignment.get("topics", []))
                if output_format == "wiki":
                    print("  Study Topics:")
                    for topic in topics:
                        print(f"  - [ ] {topic}")
                else:
                    print("  Study Topics:")
                    for topic in topics:
                        print(f"    - {topic}")
            print()  # Spacer between assignments

    # --- Study Topics for Soon Assignments ---
    if upcoming_assignments:
        # Get assignments due within the next 5 days
        soon_assignments = [
            a
            for a in upcoming_assignments
            if (datetime.strptime(a["date"], "%Y-%m-%d").date() - today_date).days <= 5
        ]

        if soon_assignments:
            header = "Study for Upcoming Assignments"
            if output_format == "wiki":
                print(f"== {header} ==")
            else:
                print(f"- {header} -")

            for assignment in soon_assignments:
                due_date = datetime.strptime(assignment["date"], "%Y-%m-%d").date()
                days_left = (due_date - today_date).days

                if output_format == "wiki":
                    print(
                        f"* *{assignment['name']}* - Due in {days_left} day(s) ({assignment['date']})"
                    )
                    if assignment.get("location"):
                        print(f"  Location: {assignment['location']}")
                    topics = parse_topics(assignment.get("topics", []))
                    if topics:
                        for topic in topics:
                            print(f"  - [ ] {topic}")
                else:
                    print(
                        f"\n*{assignment['name']}* (Due in {days_left} days - {assignment['date']})"
                    )
                    if assignment.get("location"):
                        print(f"  Location: {assignment['location']}")
                    topics = parse_topics(assignment.get("topics", []))
                    if topics:
                        print("  Topics:")
                        for topic in topics:
                            print(f"    - {topic}")
                print()

        # Show other upcoming assignments (beyond 5 days) in a summary
        later_assignments = [
            a
            for a in upcoming_assignments
            if (datetime.strptime(a["date"], "%Y-%m-%d").date() - today_date).days > 5
        ]

        if later_assignments:
            header = "Later This Month"
            if output_format == "wiki":
                print(f"== {header} ==")
            else:
                print(f"- {header} -")

            for assignment in later_assignments[:5]:  # Show next 5
                due_date = datetime.strptime(assignment["date"], "%Y-%m-%d").date()
                days_left = (due_date - today_date).days

                if output_format == "wiki":
                    print(
                        f"* *{assignment['name']}* - {assignment['date']} ({days_left} days)"
                    )
                else:
                    print(
                        f"  {assignment['name']} - {assignment['date']} ({days_left} days)"
                    )

    if not todays_assignments and not upcoming_assignments:
        print(
            "Nothing on the schedule. Take a well-deserved break or review old material!"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a study plan from a YAML file."
    )
    parser.add_argument(
        "--wiki",
        action="store_true",
        help="Output the plan in VimWiki checklist format.",
    )
    args = parser.parse_args()

    output_mode = "wiki" if args.wiki else "text"

    # You could make this an argument as well
    generate_study_plan("plans/microbiology.yaml", output_format=output_mode)
