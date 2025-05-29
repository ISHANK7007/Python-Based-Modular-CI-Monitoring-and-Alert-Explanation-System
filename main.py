# main.py

import os
from ingestion import create_ingestor
from tokenization.pipeline_factory import TokenizationPipelineFactory
from core.models import LogLine
from utils.buffered_stream_reader import BufferedStreamReader

# MODE: "github", "gitlab", "auto"
MODE = "auto"

def write_sample_log(provider, path):
    with open(path, "w", encoding="utf-8") as f:
        if provider == "github":
            f.write("2023-05-15T10:11:22.3456789Z [error] Build failed\n")
            f.write("##[group]Build Step\n")
            f.write("2023-05-15T10:11:23.1234567Z [info] Running tests\n")
            f.write("##[endgroup]\n")
            f.write("##[warning]Deprecated API used file=main.py,line=42,endLine=42,col=5,endColumn=10\n")
        elif provider == "gitlab":
            f.write("section_start:1716816585:setup[collapsed=true]\n")
            f.write("2023-06-15T14:23:41.123Z Initializing environment\n")
            f.write("section_end:1716816590:setup\n")
            f.write("2023-06-15T14:23:42.456Z Running build step\n")
            f.write("2023-06-15T14:23:43.789Z Compilation successful\n")
        else:
            f.write("UNRECOGNIZED LOG LINE FORMAT\n")

def test_auto_ingestor(log_path):
    with open(log_path, "r", encoding="utf-8") as f:
        ingestor = create_ingestor(f)
        section_map = {}
        for log in ingestor.stream_log():
            section = log.section or "Uncategorized"
            section_map.setdefault(section, 0)
            section_map[section] += 1
            print(log.get_context_summary())
            print(log.to_json(indent=2))

        print("\n=== Step Summary ===")
        for section, count in section_map.items():
            print(f"{section}: {count} lines")

def test_pipeline(log_path):
    print("\n--- Tokenization Pipeline Output ---\n")
    stream = BufferedStreamReader(log_path)
    log_lines = (LogLine.from_raw(line, idx + 1) for idx, line in enumerate(stream))
    pipeline = TokenizationPipelineFactory.create_default_pipeline()
    for segment in pipeline.process(log_lines):
        print(f"[Segment {segment.segment_id}] {segment.segment_type.name} | Severity: {segment.severity}")
        print(f"Line Range: {segment.line_range}")
        print(f"Contains Failure: {segment.contains_failure}, Errors: {segment.contains_error}, Warnings: {segment.contains_warning}")
        print(f"Text:\n{segment.get_text()}\n")

if __name__ == "__main__":
    sample_path = "detected_log.txt"
    provider = MODE if MODE in ["github", "gitlab"] else "github"
    write_sample_log(provider, sample_path)

    print("\n--- Ingestor Output ---\n")
    test_auto_ingestor(sample_path)

    test_pipeline(sample_path)

    os.remove(sample_path)
