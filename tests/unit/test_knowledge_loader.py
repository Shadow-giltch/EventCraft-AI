from pathlib import Path

from eventcraft.knowledge.loader import KnowledgeRepository


def test_knowledge_repository_loads_all_templates():
    repo = KnowledgeRepository.load_from_directory()
    for et in ["wedding", "birthday", "community"]:
        kb = repo.get(et)
        assert kb.event_type == et
        assert len(kb.budget_categories) >= 3
        assert len(kb.milestones) >= 3
        assert len(kb.run_of_show) >= 3
        assert len(kb.vendor_categories) >= 2


def test_knowledge_repository_missing_file_raises(tmp_path: Path):
    import pytest

    with pytest.raises(FileNotFoundError):
        KnowledgeRepository.load_from_directory(tmp_path)
