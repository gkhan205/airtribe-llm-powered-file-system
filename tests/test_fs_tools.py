"""Tests for fs_tools.py. Run with: pytest"""

import os

from fs_tools import list_files, read_file, search_in_file, write_file

RESUMES_FOLDER = "sample_data/resumes"


# ---------- read_file ----------


def test_read_txt_file():
    result = read_file(os.path.join(RESUMES_FOLDER, "resume_alex_johnson.txt"))
    assert result["success"] is True
    assert "Alex Johnson" in result["content"]
    assert result["metadata"]["extension"] == ".txt"


def test_read_pdf_file():
    result = read_file(os.path.join(RESUMES_FOLDER, "resume_john_doe.pdf"))
    assert result["success"] is True
    assert "John Doe" in result["content"]
    assert result["metadata"]["word_count"] > 0


def test_read_docx_file():
    result = read_file(os.path.join(RESUMES_FOLDER, "resume_jane_smith.docx"))
    assert result["success"] is True
    assert "Jane Smith" in result["content"]


def test_read_file_has_metadata():
    result = read_file(os.path.join(RESUMES_FOLDER, "resume_john_doe.pdf"))
    metadata = result["metadata"]
    assert metadata["name"] == "resume_john_doe.pdf"
    assert metadata["size_bytes"] > 0
    assert "modified" in metadata


def test_read_missing_file():
    result = read_file("does_not_exist.pdf")
    assert result["success"] is False
    assert "not found" in result["error"]


def test_read_unsupported_file(tmp_path):
    image = tmp_path / "photo.png"
    image.write_bytes(b"fake image")
    result = read_file(str(image))
    assert result["success"] is False
    assert "Unsupported" in result["error"]


def test_read_broken_pdf(tmp_path):
    broken = tmp_path / "broken.pdf"
    broken.write_text("this is not really a pdf")
    result = read_file(str(broken))
    assert result["success"] is False


def test_read_folder_instead_of_file():
    result = read_file(RESUMES_FOLDER)
    assert result["success"] is False


# ---------- list_files ----------


def test_list_all_files():
    files = list_files(RESUMES_FOLDER)
    assert len(files) == 8
    names = [file["name"] for file in files]
    assert "resume_john_doe.pdf" in names


def test_list_files_has_metadata():
    files = list_files(RESUMES_FOLDER)
    for file in files:
        assert "name" in file
        assert "size_bytes" in file
        assert "modified" in file


def test_list_only_pdf_files():
    files = list_files(RESUMES_FOLDER, ".pdf")
    assert len(files) == 3
    for file in files:
        assert file["name"].endswith(".pdf")


def test_list_files_extension_without_dot():
    assert len(list_files(RESUMES_FOLDER, "docx")) == 3


def test_list_files_skips_folders_and_hidden_files(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / ".hidden").write_text("secret")
    (tmp_path / "subfolder").mkdir()
    files = list_files(str(tmp_path))
    assert [file["name"] for file in files] == ["a.txt"]


def test_list_missing_folder():
    assert list_files("no_such_folder") == []


# ---------- write_file ----------


def test_write_file(tmp_path):
    path = tmp_path / "notes.txt"
    result = write_file(str(path), "Hello world")
    assert result["success"] is True
    assert path.read_text() == "Hello world"


def test_write_file_creates_folders(tmp_path):
    path = tmp_path / "output" / "summaries" / "summary.txt"
    result = write_file(str(path), "Summary")
    assert result["success"] is True
    assert path.exists()


def test_write_then_read(tmp_path):
    path = str(tmp_path / "summary.txt")
    write_file(path, "Python developer")
    assert read_file(path)["content"] == "Python developer"


def test_write_file_error(tmp_path):
    # writing to a folder path should fail
    result = write_file(str(tmp_path), "text")
    assert result["success"] is False


# ---------- search_in_file ----------


def test_search_finds_keyword():
    result = search_in_file(os.path.join(RESUMES_FOLDER, "resume_john_doe.pdf"), "Python")
    assert result["success"] is True
    assert result["match_count"] > 0


def test_search_is_case_insensitive():
    path = os.path.join(RESUMES_FOLDER, "resume_john_doe.pdf")
    lower = search_in_file(path, "python")
    upper = search_in_file(path, "PYTHON")
    assert lower["match_count"] == upper["match_count"]


def test_search_returns_context(tmp_path):
    path = tmp_path / "resume.txt"
    path.write_text("Line one\nI know Python well\nLine three")
    result = search_in_file(str(path), "python")
    match = result["matches"][0]
    assert match["line_number"] == 2
    assert match["line"] == "I know Python well"
    assert match["context"] == "Line one I know Python well Line three"


def test_search_no_matches():
    result = search_in_file(os.path.join(RESUMES_FOLDER, "resume_alex_johnson.txt"), "Python")
    assert result["success"] is True
    assert result["match_count"] == 0


def test_search_empty_keyword():
    result = search_in_file(os.path.join(RESUMES_FOLDER, "resume_john_doe.pdf"), "  ")
    assert result["success"] is False


def test_search_missing_file():
    result = search_in_file("missing.txt", "python")
    assert result["success"] is False
