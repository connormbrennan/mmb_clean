"""
Purpose:
    Audit model-characteristic codings with Gemini 3.1 Pro using native PDFs
    uploaded to the Files API and reused through explicit Context Caching.

Inputs:
    ../input/Model_Characteristics_corrections.xlsx
    ../input/mmb_model_paper_map.md
    ../input/model_paper_files.csv
    ../input/models/*/*.mod
    ../input/papers/*.pdf
    ../../../../config/params.yaml

Outputs:
    ../output/model_audit.csv
    ../output/gemini_all_answers.csv
    ../output/gemini_raw_responses.jsonl
    ../output/cache_manifest.csv
    ../output/progress.log
    ../output/classifying_api_run_summary.txt

Run:
    make run from tasks/data/classifying_api/code/
"""



from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import csv
import json
import os
import re
import shutil
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile


code_dir = Path(__file__).resolve().parent
task_dir = code_dir.parent
repo_dir = task_dir.parents[2]
input_dir = task_dir / "input"
papers_dir = input_dir / "papers"
models_dir = input_dir / "models"
output_dir = task_dir / "output"
config_path = repo_dir / "config" / "params.yaml"

model_characteristics_path = input_dir / "Model_Characteristics_corrections.xlsx"
model_paper_map_path = input_dir / "mmb_model_paper_map.md"
model_paper_files_path = input_dir / "model_paper_files.csv"

audit_path = output_dir / "model_audit.csv"
answers_path = output_dir / "gemini_all_answers.csv"
raw_responses_path = output_dir / "gemini_raw_responses.jsonl"
cache_manifest_path = output_dir / "cache_manifest.csv"
progress_path = output_dir / "progress.log"
summary_path = output_dir / "classifying_api_run_summary.txt"
MAX_PDF_BYTES = 50 * 1024 * 1024


def parse_scalar(value):
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if value.lower() in ["true", "yes"]:
        return 1
    if value.lower() in ["false", "no"]:
        return 0
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def read_params():
    params = {}
    current_key = None
    in_section = False
    if not config_path.exists():
        return params
    with open(config_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if line == "classifying_api:":
                in_section = True
                continue
            if in_section and not line.startswith(" "):
                in_section = False
            if not in_section:
                continue
            stripped = line.strip()
            if stripped.startswith("- ") and current_key is not None:
                params[current_key].append(parse_scalar(stripped[2:]))
                continue
            if ":" in stripped:
                key, value = stripped.split(":", 1)
                key = key.strip()
                value = value.strip()
                if value:
                    params[key] = parse_scalar(value)
                    current_key = None
                else:
                    params[key] = []
                    current_key = key
    return params


def clean_text(value):
    if value is None:
        return ""
    return str(value).replace("\u00a0", " ").strip()


def column_number(cell_ref):
    letters = re.sub(r"[^A-Z]", "", cell_ref.upper())
    value = 0
    for letter in letters:
        value = value * 26 + ord(letter) - ord("A") + 1
    return value


def text_from_xml_nodes(parent, tag):
    pieces = []
    for node in parent.iter(tag):
        if node.text:
            pieces.append(node.text)
    return "".join(pieces)


def parse_boolean(value):
    text = clean_text(value).lower()
    if text in ["true", "t", "yes", "y", "1"]:
        return True
    if text in ["false", "f", "no", "n", "0", "no mention", "none"]:
        return False
    if text.startswith("true"):
        return True
    if text.startswith("false"):
        return False
    return None


def first_percent(value):
    text = clean_text(value).replace(",", "")
    percent_match = re.search(r"(-?\d+(?:\.\d+)?)\s*%", text)
    if percent_match:
        return float(percent_match.group(1))
    number_match = re.search(r"^-?\d+(?:\.\d+)?$", text)
    if number_match:
        number = float(number_match.group(0))
        if 0 <= number <= 1:
            return number * 100
        if 0 <= number <= 100:
            return number
    return None


def first_year(value):
    text = clean_text(value)
    year_match = re.search(r"(18|19|20)\d{2}", text)
    if year_match:
        return int(year_match.group(0))
    if re.search(r"^\d+(?:\.0+)?$", text):
        number = int(float(text))
        if 1800 <= number <= 2100:
            return number
    return None


def normalize_category(value):
    text = clean_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    replacements = {
        "calvo": "calvo",
        "rotemberg": "rotemberg",
        "other": "other",
        "all sectors": "all sectors",
        "final goods firms": "final goods firms",
        "final goods": "final goods firms",
        "intermediate goods firms": "intermediate goods firms",
        "intermediate goods": "intermediate goods firms",
        "wage contracting": "wage contracting",
        "contracting": "wage contracting",
        "bargaining": "bargaining",
        "prev price inflation": "prev price inflation",
        "previous price inflation": "prev price inflation",
        "lagged price inflation": "prev price inflation",
        "prev wage inflation": "prev wage inflation",
        "previous wage inflation": "prev wage inflation",
        "lagged wage inflation": "prev wage inflation",
        "steady state inflation": "steady state inflation",
        "multiple": "multiple",
        "prev wages": "prev wages",
        "previous wages": "prev wages",
        "partial": "partial",
        "full": "full",
    }
    for key, replacement in replacements.items():
        if key in text:
            return replacement
    return text


def answer_differs(variable, spreadsheet_value, gemini_answer):
    if variable in boolean_variables:
        sheet_bool = parse_boolean(spreadsheet_value)
        answer_bool = parse_boolean(gemini_answer)
        if sheet_bool is None or answer_bool is None:
            return clean_text(spreadsheet_value).lower() != clean_text(gemini_answer).lower()
        return sheet_bool != answer_bool
    if variable in percent_variables:
        sheet_percent = first_percent(spreadsheet_value)
        answer_percent = first_percent(gemini_answer)
        if sheet_percent is not None and answer_percent is not None:
            return abs(sheet_percent - answer_percent) > 0.01
        return clean_text(spreadsheet_value).lower() != clean_text(gemini_answer).lower()
    if variable in date_variables:
        sheet_year = first_year(spreadsheet_value)
        answer_year = first_year(gemini_answer)
        if sheet_year is not None and answer_year is not None:
            return sheet_year != answer_year
        return clean_text(spreadsheet_value).lower() != clean_text(gemini_answer).lower()
    return normalize_category(spreadsheet_value) != normalize_category(gemini_answer)


def estimation_method_from_row(row):
    estimated_text = clean_text(row.get("Estimated"))
    calibrated_text = clean_text(row.get("Calibrated"))
    estimated_bool = parse_boolean(estimated_text)
    calibrated_bool = parse_boolean(calibrated_text)

    # During the transition, support either the old two-boolean coding or
    # a single already-condensed Estimated/Calibrated column.
    if estimated_bool is None and normalize_category(estimated_text) in ["estimated", "calibrated"]:
        return estimated_text
    if estimated_bool is True and calibrated_bool is not True:
        return "Estimated"
    if calibrated_bool is True and estimated_bool is not True:
        return "Calibrated"
    if estimated_bool is True and calibrated_bool is True:
        return "Estimated and Calibrated"
    if estimated_bool is False and calibrated_bool is False:
        return "Neither"
    if estimated_bool is True:
        return "Estimated"
    if calibrated_bool is True:
        return "Calibrated"
    return estimated_text


def spreadsheet_coding(model, variable):
    if variable == "Estimated":
        return estimation_method_from_row(model_rows[model])
    return clean_text(model_rows[model].get(variable))


def parent_answer_allows_question(parent, parent_answer):
    parent_answer = clean_text(parent_answer)
    if parent == "Estimated":
        if not parent_answer:
            return True
        return normalize_category(parent_answer) == "estimated"
    return parse_boolean(parent_answer) is not False


def append_csv_row(path, fieldnames, row):
    file_exists = path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_csv_rows(path):
    if not path.exists():
        return []
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_raw_response(row):
    with open(raw_responses_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=True) + "\n")


def log_progress(model, variable, status):
    timestamp = datetime.now(timezone.utc).isoformat()
    with open(progress_path, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} | {model} | {variable} | {status}\n")


def response_text(response):
    text = getattr(response, "text", None)
    if text:
        return text
    candidates = getattr(response, "candidates", None) or []
    pieces = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            part_text = getattr(part, "text", None)
            if part_text:
                pieces.append(part_text)
    return "\n".join(pieces).strip()


def partial_json_string_value(text, field):
    match = re.search(rf'"{field}"\s*:\s*"', text)
    if not match:
        unquoted_match = re.search(rf'"{field}"\s*:\s*([^,\}}\n]+)', text)
        if unquoted_match:
            return clean_text(unquoted_match.group(1).strip().strip('"'))
        return ""

    raw_value = []
    escaped = False
    for char in text[match.end():]:
        if escaped:
            raw_value.append("\\" + char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            break
        raw_value.append(char)

    raw_text = "".join(raw_value)
    try:
        return clean_text(json.loads(f'"{raw_text}"'))
    except json.JSONDecodeError:
        return clean_text(raw_text.replace('\\"', '"').replace("\\\\", "\\"))


def parse_json_answer(text, allow_partial):
    cleaned = clean_text(text)
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            if not allow_partial:
                return None
            answer = partial_json_string_value(cleaned, "answer")
            explanation = partial_json_string_value(cleaned, "explanation")
            confidence = partial_json_string_value(cleaned, "confidence")
            if not answer:
                return None
            if not explanation:
                explanation = cleaned
            return {
                "answer": answer,
                "explanation": explanation,
                "confidence": confidence,
            }
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            if not allow_partial:
                return None
            answer = partial_json_string_value(match.group(0), "answer")
            explanation = partial_json_string_value(match.group(0), "explanation")
            confidence = partial_json_string_value(match.group(0), "confidence")
            if not answer:
                return None
            if not explanation:
                explanation = cleaned
            return {
                "answer": answer,
                "explanation": explanation,
                "confidence": confidence,
            }
    if not isinstance(parsed, dict):
        return None
    if "answer" not in parsed or "explanation" not in parsed:
        return None
    return {
        "answer": clean_text(parsed.get("answer")),
        "explanation": clean_text(parsed.get("explanation")),
        "confidence": clean_text(parsed.get("confidence")),
    }


def read_workbook_rows():
    with zipfile.ZipFile(model_characteristics_path) as workbook_zip:
        names = set(workbook_zip.namelist())
        ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        rel_ns = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}

        shared_strings = []
        if "xl/sharedStrings.xml" in names:
            shared_root = ET.fromstring(workbook_zip.read("xl/sharedStrings.xml"))
            shared_tag = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
            for item in shared_root.findall("main:si", ns):
                shared_strings.append(text_from_xml_nodes(item, shared_tag))

        workbook_root = ET.fromstring(workbook_zip.read("xl/workbook.xml"))
        first_sheet = workbook_root.find("main:sheets/main:sheet", ns)
        relationship_id = first_sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]

        rels_root = ET.fromstring(workbook_zip.read("xl/_rels/workbook.xml.rels"))
        sheet_target = None
        for relationship in rels_root.findall("rel:Relationship", rel_ns):
            if relationship.attrib.get("Id") == relationship_id:
                sheet_target = relationship.attrib["Target"]
                break
        if sheet_target is None:
            raise SystemExit("Could not resolve first worksheet in Model_Characteristics_corrections.xlsx")
        if sheet_target.startswith("/"):
            sheet_path = sheet_target.lstrip("/")
        else:
            sheet_path = str(Path("xl") / sheet_target)

        sheet_root = ET.fromstring(workbook_zip.read(sheet_path))
        parsed_rows = []
        widest_row = 0
        for row_node in sheet_root.findall("main:sheetData/main:row", ns):
            cells = {}
            for cell in row_node.findall("main:c", ns):
                ref = cell.attrib.get("r", "")
                col = column_number(ref)
                widest_row = max(widest_row, col)
                cell_type = cell.attrib.get("t")
                value = ""
                if cell_type == "inlineStr":
                    inline_node = cell.find("main:is", ns)
                    if inline_node is not None:
                        value = text_from_xml_nodes(inline_node, "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
                else:
                    value_node = cell.find("main:v", ns)
                    if value_node is not None and value_node.text is not None:
                        raw_value = value_node.text
                        if cell_type == "s":
                            value = shared_strings[int(raw_value)]
                        elif cell_type == "b":
                            value = "TRUE" if raw_value == "1" else "FALSE"
                        else:
                            value = raw_value
                cells[col] = clean_text(value)
            if cells:
                parsed_rows.append(cells)

    workbook_rows = []
    header = []
    for cells in parsed_rows:
        values = [cells.get(col, "") for col in range(1, widest_row + 1)]
        if not header and any(values):
            header = values
            continue
        if not header:
            continue
        row = {}
        for col_name, value in zip(header, values):
            if col_name:
                row[col_name] = value
        model = clean_text(row.get("Model"))
        if not model:
            continue
        if model.upper().startswith("DROP BELOW"):
            break
        workbook_rows.append(row)
    return header, workbook_rows


def read_paper_label_map():
    paper_label_by_model = {}
    with open(model_paper_map_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line.startswith("|") or line.startswith("|---"):
                continue
            pieces = [piece.strip() for piece in line.strip("|").split("|")]
            if len(pieces) < 2 or pieces[0] == "Model":
                continue
            paper_label_by_model[pieces[0]] = pieces[1]
    return paper_label_by_model


def read_pdf_manifest():
    paper_file_by_model = {}
    notes_by_model = {}
    manifest_models = []
    with open(model_paper_files_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "model" not in reader.fieldnames or "pdf_file" not in reader.fieldnames:
            raise SystemExit("../input/model_paper_files.csv must have columns: model,pdf_file")
        for row in reader:
            model = clean_text(row.get("model"))
            pdf_file = clean_text(row.get("pdf_file"))
            include_value = clean_text(row.get("include", "1"))
            if not model or not pdf_file:
                continue
            if include_value.lower() in ["0", "false", "no"]:
                continue
            manifest_models.append(model)
            paper_file_by_model[model] = pdf_file
            notes_by_model[model] = clean_text(row.get("notes"))
    manifest_counts = Counter(manifest_models)
    duplicate_manifest_models = sorted(
        model for model, count in manifest_counts.items()
        if model and count > 1
    )
    if duplicate_manifest_models:
        raise SystemExit(f"Duplicate manifest models: {duplicate_manifest_models}")
    return paper_file_by_model, notes_by_model


def model_code_path(model):
    model_dir = models_dir / model
    if not model_dir.exists():
        prefix_matches = sorted(path for path in models_dir.glob(f"{model}*") if path.is_dir())
        if len(prefix_matches) == 1:
            model_dir = prefix_matches[0]
    exact_path = model_dir / f"{model}.mod"
    if exact_path.exists():
        return exact_path
    folder_name_path = model_dir / f"{model_dir.name}.mod"
    if folder_name_path.exists():
        return folder_name_path
    mod_paths = sorted(model_dir.glob("*.mod"))
    if len(mod_paths) == 1:
        return mod_paths[0]
    return None


def read_model_code(path):
    # The prompt gets the raw Dynare code so model equations can resolve paper ambiguity.
    return path.read_text(encoding="utf-8", errors="replace").strip()


def write_summary(title, lines):
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"classifying_api {title}\n")
        f.write("=" * (16 + len(title)))
        f.write("\n\n")
        for line in lines:
            f.write(f"{line}\n")


def ensure_inputs_exist(require_api_key):
    missing_inputs = []
    for required_path in [model_characteristics_path, model_paper_map_path, model_paper_files_path]:
        if not required_path.exists():
            missing_inputs.append(str(required_path.relative_to(task_dir)))
    if not models_dir.exists():
        missing_inputs.append(str(models_dir.relative_to(task_dir)))
    if not papers_dir.exists():
        missing_inputs.append(str(papers_dir.relative_to(task_dir)))
    if missing_inputs:
        write_summary("input check failed", [f"Missing required input: {item}" for item in missing_inputs])
        raise SystemExit(f"Missing required inputs: {', '.join(missing_inputs)}")

    if require_api_key and not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        write_summary("input check failed", ["Set GEMINI_API_KEY or GOOGLE_API_KEY before running make run."])
        raise SystemExit("Set GEMINI_API_KEY or GOOGLE_API_KEY before running make run.")


def import_gemini_sdk():
    try:
        from google import genai
        from google.genai import types
    except ModuleNotFoundError as exc:
        write_summary(
            "dependency check failed",
            [
                "Install the google-genai SDK in the project environment before running this task.",
                "Package name: google-genai",
            ],
        )
        raise SystemExit("Missing dependency: google-genai") from exc
    return genai, types


def ensure_output_headers():
    if not audit_path.exists():
        write_csv(audit_path, audit_fields, [])
    if not answers_path.exists():
        write_csv(answers_path, answer_fields, [])
    if not cache_manifest_path.exists():
        write_csv(cache_manifest_path, cache_manifest_fields, [])


def progress_completed():
    completed = set()
    if not progress_path.exists():
        return completed
    with open(progress_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            pieces = [piece.strip() for piece in raw_line.split("|")]
            if len(pieces) != 4:
                continue
            if pieces[3] in ["match", "diff_logged", "unclear", "skipped", "new_variable"]:
                completed.add((pieces[1], pieces[2]))
    return completed


def load_existing_answers():
    answers = {}
    for row in read_csv_rows(answers_path):
        answers[(row["model"], row["variable"])] = row
    return answers


def dependent_variables(variable):
    dependents = []
    for question in questions:
        if question.get("parent") == variable:
            child = question["variable"]
            dependents.append(child)
            dependents.extend(dependent_variables(child))
    return dependents


def reset_unclear_outputs():
    answer_rows = read_csv_rows(answers_path)
    audit_rows = read_csv_rows(audit_path)
    pairs_to_rerun = set()

    for row in answer_rows:
        if row.get("status") == "unclear" or row.get("gemini_answer") == "UNCLEAR":
            pairs_to_rerun.add((row["model"], row["variable"]))
    for row in audit_rows:
        if row.get("right_coding") == "UNCLEAR":
            pairs_to_rerun.add((row["model"], row["variable"]))

    answer_pairs = {(row["model"], row["variable"]) for row in answer_rows}
    for model, variable in list(pairs_to_rerun):
        for child in dependent_variables(variable):
            if (model, child) in answer_pairs:
                pairs_to_rerun.add((model, child))

    if not pairs_to_rerun:
        return 0

    kept_answers = [
        row for row in answer_rows
        if (row["model"], row["variable"]) not in pairs_to_rerun
    ]
    kept_audit_rows = [
        row for row in audit_rows
        if (row["model"], row["variable"]) not in pairs_to_rerun
    ]
    write_csv(answers_path, answer_fields, kept_answers)
    write_csv(audit_path, audit_fields, kept_audit_rows)

    if progress_path.exists():
        kept_progress_lines = []
        with open(progress_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                pieces = [piece.strip() for piece in raw_line.split("|")]
                if len(pieces) == 4 and (pieces[1], pieces[2]) in pairs_to_rerun:
                    continue
                kept_progress_lines.append(raw_line)
        with open(progress_path, "w", encoding="utf-8") as f:
            f.writelines(kept_progress_lines)

    return len(pairs_to_rerun)


def request_prompt(model, paper_label, model_code, question):
    if model == 'US_FRB03':
        special_cmd = '; specifically, the model in the PDF that is the linearized FRB/US model used as the Federal Reserve Board model in Levin, Wieland, and Williams (2003)'
    else:
        special_cmd = ''

    return (
        "You are an expert economist with a deep familiarity of macroeconomic models. "
        "Your task is to classify the characteristics of a macroeconomic model based "
        "on information from an academic paper and the model's code.\n\n"
        "Do not code an attribute as present merely because the paper discusses it in "
        "motivation, literature review, robustness, empirical background, or policy "
        "discussion. Prefer equations, model-description sections, calibration/estimation "
        "tables, and appendices over verbal motivation. If the answer is uncertain, give "
        "the best machine-readable answer but report low confidence and the textual evidence. \n\n"
        f"Model: {model}\n"
        f"Paper label: {paper_label}\n\n"
        f"Question: {question['text']}\n\n"
        f"{question['answer_instruction']}\n"
        f"Use the cached native PDF as the primary source{special_cmd}. Give a short explanation under "
        "40 words, with a specific page number from the paper when possible. Return "
        'only valid JSON with keys answer, explanation, and confidence. Example: '
        '{"answer":"True","explanation":"... p. 12.","confidence":"high"}\n\n'
        "Moreover, please find the model's Dynare code below. When a paper has multiple versions "
        "of a model, use the Dynare code below as the version reflecting what we are focused on.\n\n"
        "```mod\n"
        f"{model_code}\n"
        "```"
    )


def ask_gemini(client, types, cache_name, prompt):
    config_values = {
        "cached_content": cache_name,
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
        "response_mime_type": "application/json",
    }
    if model_name.startswith("gemini-3"):
        config_values["thinking_config"] = types.ThinkingConfig(thinking_level="high")
    elif model_name.startswith("gemini-2.5"):
        config_values["thinking_config"] = types.ThinkingConfig(thinking_budget=-1)
    config = types.GenerateContentConfig(**config_values)
    for attempt in range(1, request_retry_attempts + 1):
        try:
            return client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
        except Exception as exc:
            if attempt == request_retry_attempts:
                raise
            wait_seconds = request_retry_sleep_seconds * attempt
            print(
                f"Warning: Gemini request failed on attempt {attempt} "
                f"of {request_retry_attempts}: {exc}. Retrying in {wait_seconds} seconds."
            )
            time.sleep(wait_seconds)


def upload_and_cache_pdf(client, types, model, pdf_path, paper_label):
    display_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", f"{model}-{pdf_path.stem}")[:80]

    # The SDK puts the local filename into an HTTP header during upload.
    # Copy to an ASCII-only temp filename so papers with accents upload cleanly.
    with tempfile.TemporaryDirectory(prefix="classifying_api_upload_") as temp_upload_dir:
        upload_pdf_path = Path(temp_upload_dir) / f"{display_name}.pdf"
        shutil.copy2(pdf_path, upload_pdf_path)
        uploaded_file = client.files.upload(
            file=upload_pdf_path,
            config=types.UploadFileConfig(display_name=display_name, mime_type="application/pdf"),
        )

    processing_start_time = time.monotonic()
    state_name = clean_text(getattr(getattr(uploaded_file, "state", None), "name", ""))
    while state_name == "PROCESSING":
        if time.monotonic() - processing_start_time > file_processing_timeout_seconds:
            raise SystemExit(
                f"Gemini Files API processing timed out after "
                f"{file_processing_timeout_seconds} seconds for {pdf_path}"
            )
        time.sleep(file_processing_poll_seconds)
        uploaded_file = client.files.get(name=uploaded_file.name)
        state_name = clean_text(getattr(getattr(uploaded_file, "state", None), "name", ""))
    if state_name == "FAILED":
        raise SystemExit(f"Gemini Files API failed to process {pdf_path}")

    system_instruction = (
        f"Read the model in {paper_label} like you are a PhD macroeconomist with a wealth "
        "of modeling experience. You tell things straight and directly. Do not summarize "
        "the paper. Use the cached native PDF as the primary source for model-structure "
        "questions. For author central-bank employment, use Google Search if the request "
        "provides that tool. Also use Google Search for publication dates and publication "
        "status, because the cached PDF may be a working-paper version. Give short answers "
        "with specific paper page numbers when possible."
    )

    cache_config_values = {
        "display_name": display_name,
        "system_instruction": system_instruction,
        "contents": [uploaded_file],
        "ttl": f"{cache_ttl_seconds}s",
    }
    if use_google_search_for_external_metadata:
        cache_config_values["tools"] = [types.Tool(google_search=types.GoogleSearch())]

    try:
        cache = client.caches.create(
            model=model_name,
            config=types.CreateCachedContentConfig(**cache_config_values),
        )
    except Exception:
        try:
            client.files.delete(name=uploaded_file.name)
        except Exception as delete_exc:
            print(f"Warning: failed to delete uploaded file {uploaded_file.name}: {delete_exc}")
        raise

    append_csv_row(
        cache_manifest_path,
        cache_manifest_fields,
        {
            "model": model,
            "paper_file": str(pdf_path.relative_to(input_dir)),
            "uploaded_file": uploaded_file.name,
            "uploaded_file_uri": clean_text(getattr(uploaded_file, "uri", "")),
            "cache_name": cache.name,
            "cache_ttl_seconds": cache_ttl_seconds,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        },
    )
    return uploaded_file, cache


def remaining_questions_for_model(model, completed, answers):
    remaining = []
    model_answers = {variable: row for (answer_model, variable), row in answers.items() if answer_model == model}
    for question in questions:
        variable = question["variable"]
        if (model, variable) in completed:
            continue
        parent = question.get("parent")
        if parent:
            parent_answer = clean_text(model_answers.get(parent, {}).get("gemini_answer"))
            if not parent_answer_allows_question(parent, parent_answer):
                remaining.append({"variable": variable, "skip": True})
                continue
        remaining.append(question)
    return remaining


def run_cached_audit(client, types):
    completed = progress_completed()
    answers = load_existing_answers()
    models_processed = 0
    questions_attempted = 0
    skipped_questions = 0
    diffs_logged = 0
    unclear_logged = 0
    new_variables_logged = 0

    for workbook_row in workbook_rows:
        model = workbook_row["Model"]
        if model not in paper_file_by_model:
            continue

        remaining = remaining_questions_for_model(model, completed, answers)
        if not remaining:
            continue
        if all(item.get("skip") for item in remaining):
            for item in remaining:
                variable = item["variable"]
                if (model, variable) not in completed:
                    log_progress(model, variable, "skipped")
                    completed.add((model, variable))
                    skipped_questions += 1
            continue
        if max_models_per_run and models_processed >= max_models_per_run:
            break

        pdf_path = pdf_path_by_model[model]
        paper_label = paper_label_by_model.get(model, pdf_path.stem)
        model_code = read_model_code(model_code_path_by_model[model])
        log_progress(model, "__model__", "starting_model")
        uploaded_file, cache = upload_and_cache_pdf(client, types, model, pdf_path, paper_label)
        models_processed += 1

        try:
            for question in questions:
                variable = question["variable"]
                if (model, variable) in completed:
                    continue

                parent = question.get("parent")
                if parent:
                    parent_answer = clean_text(answers.get((model, parent), {}).get("gemini_answer"))
                    if not parent_answer_allows_question(parent, parent_answer):
                        log_progress(model, variable, "skipped")
                        completed.add((model, variable))
                        skipped_questions += 1
                        continue

                prompt = request_prompt(model, paper_label, model_code, question)

                response = ask_gemini(client, types, cache.name, prompt)
                raw_text = response_text(response)
                parsed_answer = parse_json_answer(raw_text, False)

                if parsed_answer is None:
                    reask_prompt = (
                        prompt
                        + "\n\nYour previous reply was not valid JSON. Please answer again with only "
                        'valid JSON: {"answer":"...","explanation":"...","confidence":"high|medium|low"}. '
                        "Keep the explanation under 40 words."
                    )
                    response = ask_gemini(client, types, cache.name, reask_prompt)
                    raw_text = response_text(response)
                    parsed_answer = parse_json_answer(raw_text, True)

                append_raw_response(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "model": model,
                        "variable": variable,
                        "paper_file": str(pdf_path.relative_to(input_dir)),
                        "cache_name": cache.name,
                        "uploaded_file": uploaded_file.name,
                        "uploaded_file_uri": clean_text(getattr(uploaded_file, "uri", "")),
                        "usage_metadata": str(getattr(response, "usage_metadata", "")),
                        "text": raw_text,
                    }
                )

                spreadsheet_value = spreadsheet_coding(model, variable)
                if parsed_answer is None:
                    status = "unclear"
                    gemini_answer = "UNCLEAR"
                    explanation = raw_text
                    confidence = ""
                    unclear_logged += 1
                    append_csv_row(
                        audit_path,
                        audit_fields,
                        {
                            "model": model,
                            "variable": variable,
                            "right_coding": gemini_answer,
                            "explanation": explanation,
                        },
                    )
                else:
                    gemini_answer = parsed_answer["answer"]
                    explanation = parsed_answer["explanation"]
                    confidence = parsed_answer["confidence"]
                    if variable not in header:
                        status = "new_variable"
                        new_variables_logged += 1
                        append_csv_row(
                            audit_path,
                            audit_fields,
                            {
                                "model": model,
                                "variable": variable,
                                "right_coding": gemini_answer,
                                "explanation": explanation,
                            },
                        )
                    elif answer_differs(variable, spreadsheet_value, gemini_answer):
                        status = "diff_logged"
                        diffs_logged += 1
                        append_csv_row(
                            audit_path,
                            audit_fields,
                            {
                                "model": model,
                                "variable": variable,
                                "right_coding": gemini_answer,
                                "explanation": explanation,
                            },
                        )
                    else:
                        status = "match"

                append_csv_row(
                    answers_path,
                    answer_fields,
                    {
                        "model": model,
                        "variable": variable,
                        "paper_file": str(pdf_path.relative_to(input_dir)),
                        "spreadsheet_coding": spreadsheet_value,
                        "gemini_answer": gemini_answer,
                        "explanation": explanation,
                        "confidence": confidence,
                        "status": status,
                        "cache_name": cache.name,
                        "usage_metadata": str(getattr(response, "usage_metadata", "")),
                    },
                )
                answers[(model, variable)] = {
                    "model": model,
                    "variable": variable,
                    "gemini_answer": gemini_answer,
                    "status": status,
                }
                completed.add((model, variable))
                log_progress(model, variable, status)
                questions_attempted += 1
                time.sleep(request_pause_seconds)
        finally:
            try:
                client.caches.delete(name=cache.name)
            except Exception as exc:
                print(f"Warning: failed to delete cache {cache.name}: {exc}")
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception as exc:
                print(f"Warning: failed to delete uploaded file {uploaded_file.name}: {exc}")

    write_summary(
        "run summary",
        [
            f"Run timestamp UTC: {datetime.now(timezone.utc).isoformat()}",
            f"Gemini model: {model_name}",
            f"Cache TTL seconds: {cache_ttl_seconds}",
            f"Models in workbook: {len(workbook_rows)}",
            f"Models in PDF manifest: {len(paper_file_by_model)}",
            f"Models processed this run: {models_processed}",
            f"Questions attempted this run: {questions_attempted}",
            f"Conditional questions skipped this run: {skipped_questions}",
            f"Discrepancies logged this run: {diffs_logged}",
            f"Unclear answers logged this run: {unclear_logged}",
            f"New classification-only rows logged this run: {new_variables_logged}",
            f"Unclear/dependent pairs reset before run: {reset_unclear_pairs_count}",
            "No Batch API jobs were used.",
        ],
    )


questions = [
    {
        "variable": "CB_Authors",
        "text": "True or False: Does this model have authors who've worked at a central bank PRIOR to publication of the paper? Specifically search and look through the economists' CVs, websites, backgrounds, or anything else to ascertain if so. If multiple authors, report the fraction in a percentage. Consultancies, visiting scholar positions, graduate research programs, and internships do NOT count as working at a central bank. The IMF and BIS DO count as central banks.",
        "answer_instruction": "Answer as a percentage from 0% to 100%, and include a True/False statement in the explanation.",
    },
    {
        "variable": "Open", 
        "text": "True or False: Does this model have an open economy? That is, does the model include a foreign sector, exchange rate, trade, import/export prices, multi-country block, etc.?", 
        "answer_instruction": "Answer exactly True or False."
        },
    {
        "variable": "Firm_Balance_Sheet_Channel",
        "text": "True or False: Does this model include a borrower balance-sheet channel on the production-side/nonfinancial private-borrower side? Mark True only if firms, entrepreneurs, producers, or other non-bank private business borrowers have balance sheets that affect financing conditions, borrowing capacity, investment, production, or default. Count mechanisms such as net worth, leverage, collateral values, default risk, borrowing constraints, agency or monitoring costs, or an endogenous external finance premium that creates a wedge between internal and external finance. A reduced-form external-finance-premium or borrowing-spread equation counts if the spread or borrowing capacity depends on borrower balance-sheet strength and is part of the model used for quantitative analysis. Do not count household borrowing constraints, bank or intermediary balance-sheet constraints, frictionless firm financing, a purely exogenous risk-premium/spread shock, or an empirical regression outside the model. A variable such as net worth is not enough by itself; it must affect borrowing costs, borrowing quantities, investment, production, default, or another equilibrium condition. Look for the mechanism, not just the variable name.",        
        "answer_instruction": "Answer exactly True or False."
        },
    {
        "variable": "Bank_Lending_Intermediation_Channel",
        "text": "True or False: Does this model include a bank lending or financial-intermediation channel? Mark True only if banks, bankers, or financial intermediaries are modeled as distinct agents or sectors whose own balance sheets, capital, leverage, net worth, deposit or wholesale funding structure, liquidity constraints, monitoring costs, regulatory constraints, or loan/asset-supply choices affect lending rates, lending quantities, spreads, credit allocation, or asset prices. A reduced-form intermediation spread or credit-supply equation counts if it depends on intermediary balance-sheet strength, funding conditions, leverage, capital, or constraints and is part of the model used for quantitative analysis. Do not count models with no intermediaries, models where banks are only a passive veil that passes funds from savers to borrowers, models where the financing friction is entirely on the borrower side with no distinct intermediary-side mechanism, a purely exogenous spread shock, or an empirical regression outside the model. Look for the mechanism, not just the variable name.",        
        "answer_instruction": "Answer exactly True or False."
        },
    {
        "variable": "Constrained_Household_Demand_Channel",
        "text": "True or False: Does this model include a constrained household demand channel? Mark True if some households cannot fully smooth consumption, so their spending depends meaningfully on current income, liquidity, borrowing limits, collateral constraints, household debt, debt-service obligations, or binding/occasionally binding household financial constraints. Count rule-of-thumb consumers, hand-to-mouth households, liquidity-constrained households, borrower-saver or impatient-patient household structures, incomplete-markets households, housing-collateral constraints, and household debt-service channels when they affect aggregate consumption demand. These households may still be optimizing. A reduced-form consumption rule or household-demand block counts if it makes consumption depend directly on current income, liquidity, borrowing constraints, collateral, debt service, or household financial conditions and is part of the model used for quantitative analysis. Do not count a model in which all households are standard unconstrained Ricardian optimizers. Do not count the generic Euler-equation wealth effect present in ordinary representative-agent models. A household debt or asset variable is not enough by itself; it must affect consumption through liquidity, borrowing capacity, collateral, current income sensitivity, debt service, or another household-demand constraint. Look for the mechanism, not just the variable name.",        
        "answer_instruction": "Answer exactly True or False."
        },
    {
        "variable": "Real_Labor_Market_Friction",
        "text": "True or False: Does this model include real labor-market frictions beyond nominal wage stickiness? Mark True only if the labor market has a non-Walrasian or real friction such as search and matching, endogenous unemployment generated by labor-market frictions, vacancy posting, hiring costs, firing costs, separation shocks, labor-market tightness, fixed employment costs, real wage rigidity, staggered or costly employment adjustment, or bargaining that affects employment, wages, vacancies, unemployment, or other allocations. A reduced-form labor-market block counts if it is part of the model used for quantitative analysis and makes employment, unemployment, hours, hiring, separations, or real wages depend on labor-market frictions rather than only on standard competitive labor supply and demand. Do not count sticky wages alone, wage indexation alone, standard competitive labor supply and labor demand, ordinary convex disutility of labor, labor-supply shocks, or a measured unemployment variable that is not generated by a labor-market friction. Wage bargaining alone counts only if it is part of a frictional labor-market mechanism or otherwise changes real allocations beyond nominal wage stickiness. Look for the mechanism, not just the variable name.",        
        "answer_instruction": "Answer exactly True or False."
         },
    {
        "variable": "Gov_Spend", 
        "text": "True or False: Does this model have government spending in a nontrivial way that affects equilibrium? That is, does government spending enter the model as an endogenous or policy-relevant fiscal block, e.g. a fiscal rule, productive/public-capital spending, utility from public goods, debt-financed spending, or a government-spending shock central to the model? Do not count a residual exogenous demand term that is included only to close the resource constraint.", 
        "answer_instruction": "Answer exactly True or False."
        },
    {
        "variable": "Tax", 
        "text": "True or False: Does this model have taxes in a nontrivial way that affects equilibrium? That is, do tax rates or tax rules enter household/firm first-order conditions, budget constraints, labor supply, investment, consumption, pricing, debt stabilization, or other equilibrium conditions, or are present as distortionary taxation? Do not count lump-sum taxes/transfers used only to satisfy the government budget constraint.", 
        "answer_instruction": "Answer exactly True or False."
        },
    {
        "variable": "Gov_Debt", 
        "text": "True or False: Does this model have government debt in a nontrivial way that affects equilibrium? That is, is debt an economically active state variable: debt feedback in fiscal policy, sovereign/default risk, debt limits, long-term bonds, liquidity services, non-Ricardian effects, FTPL, or portfolio effects? Do not count one-period government bonds used only as a household asset and government-budget accounting device.",
        "answer_instruction": "Answer exactly True or False."
        },
    {
        "variable": "Learning", 
        "text": "True or False: Does this model have learning? Specifically, do households or firms form beliefs about a state variable? This includes Bayesian learning about a latent state or unknown parameter, learning about regimes, adaptive or least-squares learning, or any other process where agents form beliefs about the structure of the economy. Do not include simple extrapolative forecasts of future variables (e.g., expected inflation next period equals inflation this period) or diagnostic expectations.", 
        "answer_instruction": "Answer exactly True or False."
        },
    {
        "variable": "Rational_Expectations", 
        "text": "True or False: Does this model have rational expectations? That is, does the model solve agents’ expectations as model-consistent expectations given the information structure, rather than through adaptive/least-squares/Bayesian learning or exogenous expectation rules?", 
        "answer_instruction": "Answer exactly True or False."
        },
    {
        "variable": "Lagged_Terms", 
        "text": "True or False: Does this model have propagation mechanisms that depend on past variables. Specifically, mark True if the model has habit formation, investment adjustment costs, capital adjustment costs, variable capital utilization, external habits, durable goods/housing stock, financial net worth/state dependence. Do not count generic capital accumulation or exogenous AR shocks.", 
        "answer_instruction": "Answer exactly True or False."
        },
    {
        "variable": "Sticky_Prices", 
        "text": "True or False: Does this model have sticky prices? That is, do prices in the model adjust sluggishly due to some frictions? Examples include if there are Calvo pricing, Rotemberg pricing, menu costs, or any other mechanism that introduces price stickiness into the model. If the model is a descendant of Smets and Wouters (2007), assume it has sticky prices UNLESS the paper otherwise relaxes this assumption or, better yet, the model code shows no sticky prices. Also, if the model is sticky information or rational inattention, that potentially counts as sticky prices depending on whose information is sticky or whose inattention it is. Use your judgment to determine if sticky information or rational inattention in the model should be classified as sticky prices.", 
        "answer_instruction": "Answer exactly True or False."
        },
    {
        "variable": "Sticky_Price_Method", "parent": "Sticky_Prices", 
        "text": "If so, what is their sticky price method? Choose between Calvo, Rotemberg, or Other.", 
        "answer_instruction": "Answer exactly one of: Calvo, Rotemberg, Other."
        },
    {
        "variable": "Sticky_Price_Sector", "parent": "Sticky_Prices", 
        "text": "If so, in what sector do sticky prices apply? Choose between All Sectors, Final Goods Firms, Intermediate Goods Firms, or Other.", 
        "answer_instruction": "Answer exactly one of: Multiple Sectors, Final/Retail Firms, Intermediate Goods Firms, Representative Single Sector, Other."
        },
    {
        "variable": "Sticky_Wages", 
        "text": "True or False: Does this model have sticky wages? That is, do wages in the model adjust sluggishly due to some frictions? Examples include if there are Calvo wage setting, Rotemberg wage setting, or any other mechanism that introduces wage stickiness into the model. If the model is a descendant of Smets and Wouters (2007), assume it has sticky wages UNLESS the paper otherwise relaxes this assumption or, better yet, the model code shows no sticky wages. Also, if the model is sticky information or rational inattention, that potentially counts as sticky wages depending on whose information is sticky or whose inattention it is. Use your judgment to determine if sticky information or rational inattention in the model should be classified as sticky wages. Also, search-theoretic models count as sticky wages if, ulimtately, they make wages adjust sluggishly due to frictions in the labor market (for example, bargaining by itself does not necessarily imply sticky wages).", 
        "answer_instruction": "Answer exactly True or False."
        },
    {
        "variable": "Sticky_Wage_Method", "parent": "Sticky_Wages", 
        "text": "If so, what is their sticky wage method? Choose between Calvo, Rotemberg, Wage Contracting, Bargaining, or Other.", 
        "answer_instruction": "Answer exactly one of: Calvo, Rotemberg, Wage Contracting, Bargaining, Other."
        },
    {
        "variable": "Price_Indexation", 
        "text": "True or False: Does this model have price indexation? Note that this includes cases in which prices are indexed to inflation (or steady state inflation) or otherwise are set with backward-looking dynamics. If the model is a descendant of Smets and Wouters (2007), assume it has price indexation UNLESS the paper otherwise relaxes this assumption or, better yet, the model code shows no price indexation.", 
        "answer_instruction": "Answer exactly True or False."
        },
    {
        "variable": "Price_Index_Method", "parent": "Price_Indexation", 
        "text": "If so, by what method? Choose between Prev Price Inflation, Multiple (e.g., a weighted combination of past inflation and the target), Steady State Inflation, or Other.", 
        "answer_instruction": "Answer exactly one of: Prev Price Inflation, Multiple, Steady State Inflation, Other."
        },
    {
        "variable": "Price_Index_Coverage", "parent": "Price_Indexation", 
        "text": "Does price indexation have partial or full coverage? Answer one or the other. Full if non-reset prices are indexed one-for-one to the relevant inflation measure. Partial if the indexation coefficient is estimated/calibrated strictly between zero and one.", 
        "answer_instruction": "Answer exactly one of: Partial, Full."
        },
    {
        "variable": "Wage_Indexation", 
        "text": "Does this model have wage indexation? Note that this includes cases in which wages are indexed to inflation (or steady state inflation) or otherwise set with backward-looking dynamics. If the model is a descendant of Smets and Wouters (2007), assume it has wage indexation UNLESS the paper otherwise relaxes this assumption or, better yet, the model code shows no wage indexation.", 
        "answer_instruction": "Answer exactly True or False."
        },
    {
        "variable": "Wage_Index_Method", "parent": "Wage_Indexation", 
        "text": "If so, by what method? Choose between Prev Price Inflation, Prev Wage Inflation, Steady State Inflation, Multiple (e.g., a weighted combination of past wage inflation and the steady state), Prev Wages, or Other.", 
        "answer_instruction": "Answer exactly one of: Prev Price Inflation, Prev Wage Inflation, Steady State Inflation, Multiple, Prev Wages, Other."
        },
    {
        "variable": "Wage_Index_Coverage", "parent": "Wage_Indexation", 
        "text": "Does wage indexation have partial or full coverage? Full if non-reset wages are indexed one-for-one to the relevant inflation measure. Partial if the indexation coefficient is estimated/calibrated strictly between zero and one.", 
        "answer_instruction": "Answer exactly one of: Partial, Full."
        },
    {
        "variable": "Date_Pub", 
        "text": "When was this model published? Give as quarterly date. This should be the date at which the exact version of the model whose code is included below was made available. Do not use the dates of early or later drafts whose models differ from the one whose code is included below (excluding the MMB-inserted block).", 
        "answer_instruction": "Answer with the quarterly date (formatted as, for example, '2006Q4')."
        },
    {
        "variable": "Working_Paper", 
        "text": "Is this only ever published as a working paper?", 
        "answer_instruction": "Answer exactly True or False."
        },
    {
        "variable": "Published", 
        "text": "Is this model published in an academic journal? True only for peer-reviewed academic journal publication. False for working papers, central-bank reports, technical reports, NBER working papers, book chapters, and conference volumes unless separately peer-reviewed and journal-like.", 
        "answer_instruction": "Answer exactly True or False."
        },
    {
        "variable": "Estimated", 
        "text": "Was this model estimated or calibrated? Choose exactly one. Estimated means the paper formally estimates model parameters from data, for example using Bayesian estimation, maximum likelihood, GMM, SMM, or a similar estimation procedure. Calibrated means parameters are assigned externally, chosen from prior literature, or set by informal moment matching without a formal estimation procedure. If the paper contains both estimated and calibrated parameters, choose Estimated if a majority of core structural parameters are formally estimated; otherwise choose Calibrated. Do not answer Both and do not answer Neither.", 
        "answer_instruction": "Answer exactly one of: Estimated, Calibrated."
        },
    {
        "variable": "Est_Date_Range_Start", "parent": "Estimated", 
        "text": "If the previous answer is Estimated, what is the estimate date range start? Give as quarterly date. This date should be the estimation data start date of the **main** model equations (the core of the model), not that of empirical exercises contained in the paper or select parts of the model. If different observables have different starting dates, use the effective sample used for estimating the full system. Convert monthly dates to the containing quarter. Do not use the sample of robustness exercises, auxillary regressions, or isolated empirical sectons.", 
        "answer_instruction": "Answer with the quarterly date (formatted as, for example, '2006Q4')."
        },
    {
        "variable": "Est_Date_Range_End", "parent": "Estimated", 
        "text": "If the previous answer is Estimated, what is the estimate date range end? Give as quarterly date. This date should be the estimation data end date of the **main** model equations (the core of the model), not that of empirical exercises contained in the paper or select parts of the model. If different observables have different starting dates, use the effective sample used for estimating the full system. Convert monthly dates to the containing quarter. Do not use the sample of robustness exercises, auxillary regressions, or isolated empirical sectons.", 
        "answer_instruction": "Answer with the quarterly date (formatted as, for example, '2006Q4')."
        },
]


boolean_variables = {
    "Open",
    "Gov_Spend",
    "Tax",
    "Gov_Debt",
    "Learning",
    "Rational_Expectations",
    "Lagged_Terms",
    "Firm_Balance_Sheet_Channel",
    "Bank_Lending_Intermediation_Channel",
    "Constrained_Household_Demand_Channel",
    "Real_Labor_Market_Friction",
    "Sticky_Prices",
    "Sticky_Wages",
    "Price_Indexation",
    "Wage_Indexation",
    "Working_Paper",
    "Published",
}
percent_variables = {"CB_Authors"}
date_variables = {"Date_Pub", "Est_Date_Range_Start", "Est_Date_Range_End"}
SEARCH_VARIABLES = {"CB_Authors", "Date_Pub", "Working_Paper", "Published"}

# These variables may not exist yet in Model_Characteristics_corrections.xlsx.
# If absent from the workbook, their Gemini classifications are still written to
# gemini_all_answers.csv and model_audit.csv with status="new_variable".
classification_only_variables = {
    "Firm_Balance_Sheet_Channel",
    "Bank_Lending_Intermediation_Channel",
    "Constrained_Household_Demand_Channel",
    "Real_Labor_Market_Friction",
}
all_variables = [question["variable"] for question in questions]

audit_fields = ["model", "variable", "right_coding", "explanation"]
answer_fields = [
    "model",
    "variable",
    "paper_file",
    "spreadsheet_coding",
    "gemini_answer",
    "explanation",
    "confidence",
    "status",
    "cache_name",
    "usage_metadata",
]
cache_manifest_fields = [
    "model",
    "paper_file",
    "uploaded_file",
    "uploaded_file_uri",
    "cache_name",
    "cache_ttl_seconds",
    "created_at_utc",
]


params = read_params()
model_name = str(params.get("gemini_model", "gemini-3.1-pro-preview"))
cache_ttl_seconds = int(params.get("cache_ttl_seconds", 172800))
temperature = float(params.get("temperature", 0))
max_output_tokens = int(params.get("max_output_tokens", 1024))
file_processing_poll_seconds = float(params.get("file_processing_poll_seconds", 2))
file_processing_timeout_seconds = float(params.get("file_processing_timeout_seconds", 600))
request_pause_seconds = float(params.get("request_pause_seconds", 1))
request_retry_attempts = int(params.get("request_retry_attempts", 4))
request_retry_sleep_seconds = float(params.get("request_retry_sleep_seconds", 20))
max_models_per_run = int(params.get("max_models_per_run", 0))
rerun_unclear_outputs_flag = int(params.get("rerun_unclear_outputs", 0))
use_google_search_for_external_metadata = int(
    params.get("use_google_search_for_external_metadata", params.get("use_google_search_for_cb_authors", 1))
)
run_stage = clean_text(os.environ.get("CLASSIFYING_API_STAGE", params.get("run_stage", "status"))).lower()
reset_unclear_pairs_count = 0


print("Classifying v2 run controls")
for key, value in {
    "model_name": model_name,
    "cache_ttl_seconds": cache_ttl_seconds,
    "temperature": temperature,
    "max_models_per_run": max_models_per_run,
    "run_stage": run_stage,
}.items():
    print(f"{key}: {value}")


output_dir.mkdir(parents=True, exist_ok=True)
ensure_inputs_exist(run_stage == "run")
header, workbook_rows = read_workbook_rows()
workbook_counts = Counter(clean_text(row.get("Model")) for row in workbook_rows)
duplicate_workbook_models = sorted(
    model for model, count in workbook_counts.items()
    if model and count > 1
)
if duplicate_workbook_models:
    raise SystemExit(f"Duplicate workbook models: {duplicate_workbook_models}")
model_rows = {clean_text(row["Model"]): row for row in workbook_rows if clean_text(row.get("Model"))}
paper_label_by_model = read_paper_label_map()
paper_file_by_model, notes_by_model = read_pdf_manifest()

missing_columns = sorted(set(all_variables) - set(header) - classification_only_variables)
missing_models = sorted(set(paper_file_by_model) - set(model_rows))
workbook_models_missing_manifest = sorted(set(model_rows) - set(paper_file_by_model))
pdf_path_by_model = {}
missing_pdfs = []
model_code_path_by_model = {}
missing_model_code = []
for model, pdf_file in paper_file_by_model.items():
    candidate_path = Path(pdf_file)
    if not candidate_path.is_absolute():
        candidate_path = papers_dir / pdf_file
    if not candidate_path.exists():
        missing_pdfs.append(f"{model}: {candidate_path.relative_to(task_dir)}")
    elif candidate_path.stat().st_size > MAX_PDF_BYTES:
        missing_pdfs.append(
            f"{model}: PDF exceeds 50MB Gemini document limit: {candidate_path.relative_to(task_dir)}"
        )
    pdf_path_by_model[model] = candidate_path
    candidate_model_code_path = model_code_path(model)
    if candidate_model_code_path is None:
        missing_model_code.append(f"{model}: {(models_dir / model).relative_to(task_dir)}")
    else:
        model_code_path_by_model[model] = candidate_model_code_path

if missing_columns or missing_models or workbook_models_missing_manifest or missing_pdfs or missing_model_code:
    lines = []
    for variable in missing_columns:
        lines.append(f"Workbook is missing question variable column: {variable}")
    for model in missing_models:
        lines.append(f"Manifest model is not in workbook: {model}")
    for model in workbook_models_missing_manifest:
        lines.append(f"Workbook model is missing from manifest: {model}")
    for pdf in missing_pdfs:
        lines.append(f"Manifest PDF is missing: {pdf}")
    for model_code in missing_model_code:
        lines.append(f"Model .mod file is missing or ambiguous: {model_code}")
    write_summary("input check failed", lines)
    raise SystemExit("Workbook, manifest, PDF folder, and model-code folder do not line up.")

ensure_output_headers()
if run_stage == "run" and rerun_unclear_outputs_flag:
    reset_unclear_pairs_count = reset_unclear_outputs()


print(f"Workbook models: {len(workbook_rows)}")
print(f"PDF manifest models: {len(paper_file_by_model)}")
print(f"Question variables: {len(all_variables)}")
print(f"Missing PDFs: {len(missing_pdfs)}")


if run_stage == "status":
    completed = progress_completed()
    lines = [
        f"Models in workbook: {len(workbook_rows)}",
        f"Models in PDF manifest: {len(paper_file_by_model)}",
        f"Gemini model: {model_name}",
        f"Cache TTL seconds: {cache_ttl_seconds}",
        f"Completed model-question pairs in progress.log: {len(completed)}",
        "Mode: Context Caching with ordinary generate_content calls; Batch API is not used.",
    ]
    write_summary("status", lines)
elif run_stage == "run":
    completed = progress_completed()
    answers = load_existing_answers()
    pending_models = []
    pending_pairs = 0
    for workbook_row in workbook_rows:
        model = workbook_row["Model"]
        if model not in paper_file_by_model:
            continue
        remaining = remaining_questions_for_model(model, completed, answers)
        pending_question_count = sum(1 for item in remaining if not item.get("skip"))
        if pending_question_count:
            pending_models.append(model)
            pending_pairs += pending_question_count
    write_summary(
        "run preflight",
        [
            f"Run timestamp UTC: {datetime.now(timezone.utc).isoformat()}",
            f"Run stage: {run_stage}",
            f"Gemini model: {model_name}",
            f"Models in workbook: {len(workbook_rows)}",
            f"Models in PDF manifest: {len(paper_file_by_model)}",
            f"Completed model-question pairs in progress.log: {len(completed)}",
            f"Models with pending non-skipped questions: {len(pending_models)}",
            f"Pending non-skipped model-question pairs: {pending_pairs}",
            f"First pending models: {', '.join(pending_models[:10])}",
            "If this file remains a run preflight summary, the run stopped before final completion.",
        ],
    )
    genai, types = import_gemini_sdk()
    client = genai.Client()
    run_cached_audit(client, types)
else:
    raise SystemExit(f"Unknown CLASSIFYING_API_STAGE: {run_stage}")


if summary_path.exists():
    print(summary_path.read_text())
