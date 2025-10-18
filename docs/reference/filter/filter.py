import subprocess
import sys
from typing import Any, cast

from griffe import Module
import griffe
import panflute as pf  # type: ignore

from parse import DocParseOptions, parse_docs
from render import render_docs
from commands import make_command_docs


def main() -> Any:
    # create options
    module = cast(Module, griffe.load("inspect_scout"))
    sha = (
        subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True)
        .stdout.decode()
        .strip()
    )
    source_url = f"https://github.com/meridianlabs-ai/inspect_scout/blob/{sha}/src"
    parse_options = DocParseOptions(module=module, source_url=source_url)

    # python api -- convert h3 into reference
    def python_api(elem: pf.Element, doc: pf.Doc) -> Any:
        if isinstance(elem, pf.Header) and elem.level == 3:
            title = pf.stringify(doc.metadata["title"])
            if not title.startswith("inspect_scout"):
                title =  pf.stringify(doc.metadata["reference"])
                
            if title.startswith("inspect_scout"):

                target = elem.attributes.get("reference", pf.stringify(elem.content))
                if title.startswith("inspect_scout."):
                    # get target object
                    module = title.removeprefix("inspect_scout.")
                    object = f"{module}.{target}"
                else:
                    object = target

                # parse docs
                docs = parse_docs(object, parse_options)

                # render docs
                return render_docs(elem, docs)
            
            else:
                return elem
            
    # click cli
    def click_cli(elem: pf.Element, doc: pf.Doc) -> None:
        if isinstance(elem, pf.Doc):
            title = pf.stringify(doc.metadata["title"])
            if title.startswith("scout "):
                command = title.split(" ")[1]
                docs = "\n".join(list(make_command_docs(command)))
                doc.content.append(pf.RawBlock(docs, "markdown"))
               

    return pf.run_filters([python_api, click_cli])


if __name__ == "__main__":
    main()
