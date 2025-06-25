#!/bin/bash

TOPIC_DIR="notes/topics"
GLOSSARY_FILE="notes/glossary.wiki"
TEMP_FILE="$(mktemp)"

echo "= Glossary =" > "$TEMP_FILE"
echo "" >> "$TEMP_FILE"

# Collect entries
declare -A entries

for filepath in "$TOPIC_DIR"/*.wiki; do
    [ -e "$filepath" ] || continue
    filename=$(basename "$filepath" .wiki)
    displayname="${filename^}"  # Capitalize first letter

    # Try to extract first non-empty, non-header line as description
    description=$(grep -v '^=\|^$' "$filepath" | head -n 1 | sed 's/^ *//')
    [ -z "$description" ] && description="No description yet."

    first_letter=${displayname:0:1}  # First letter for grouping

    # Format: [[link|Display]] :: Description
    entry="* [[topics/${filename}|${displayname}]] :: ${description}"

    entries["$first_letter"]+="${entry}\n"
done

# Sort and write entries under each letter group
for letter in $(printf "%s\n" "${!entries[@]}" | sort); do
    echo "== ${letter^^} ==" >> "$TEMP_FILE"
    printf "${entries[$letter]}" | sort -f >> "$TEMP_FILE"
    echo "" >> "$TEMP_FILE"
done

mv "$TEMP_FILE" "$GLOSSARY_FILE"
echo "✅ Glossary regenerated at $GLOSSARY_FILE"

