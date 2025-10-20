#!/bin/bash

files=("index" "workflow" "scanners" "results" "transcripts" "parallelism" "options" "reference/scanning" "reference/transcript" "reference/scanner" "reference/async") 


if [ "$QUARTO_PROJECT_RENDER_ALL" = "1" ]; then
    llms_guide="_site/llms-guide.txt"
    rm -f "${llms_guide}"
    llms_full="_site/llms-full.txt"
    rm -f "${llms_full}"
    mv _quarto.yml _quarto.yml.bak
    for file in "${files[@]}"; do
        echo "llms: ${file}.qmd"
        quarto render "${file}.qmd" --to gfm-raw_html --quiet --no-execute
        output_file="${file}.md"
        cat "${output_file}" >> "${llms_full}"
        echo "" >> "${llms_full}"
        if [[ ! "${file}" == reference/* ]]; then
            cat "${output_file}" >> "${llms_guide}"
            echo "" >> "${llms_guide}"
        fi
        mv $output_file "_site/${file}.html.md"
    done
    mv _quarto.yml.bak _quarto.yml
fi


