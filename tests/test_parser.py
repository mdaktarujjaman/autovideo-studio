from autovideo.parser import parse


def test_parser_ignores_bom(tmp_path):
    script = tmp_path / "script.txt"
    script.write_bytes("\ufeff@voice bn-BD-PradeepNeural\n\nএকটি বাক্য।\n".encode("utf-8"))
    config, scenes = parse(script)
    assert config["voice"] == "bn-BD-PradeepNeural"
    assert len(scenes) == 1