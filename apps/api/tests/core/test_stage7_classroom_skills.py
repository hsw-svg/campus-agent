import json
from uuid import uuid4

import pytest

from app.agents.contracts import ContextArtifact
from app.core.errors import AppError
from app.skills.classroom_activity import ClassroomActivityPackageSkill
from app.skills.classroom_observation import ClassroomObservationSkill
from app.skills.classroom_summary import ClassroomSummarySkill


def test_activity_package_keeps_valid_items_and_reports_invalid_items() -> None:
    raw = """
    {
      "topic": "Python 列表",
      "objectives": ["区分索引与切片"],
      "activities": [
        {"type": "multiple_choice", "title": "诊断", "duration_minutes": 5,
         "prompt": "下列哪项是切片？", "options": ["A. a[0]", "B. a[1:3]"], "answer": "B"},
        {"type": "multiple_choice", "duration_minutes": 5,
         "prompt": "缺答案的题", "options": ["A", "B"]},
        {"type": "discussion", "duration_minutes": 5,
         "prompt": "解释两者区别", "rubric": ["能说明返回值差异"]}
      ]
    }
    """

    result = ClassroomActivityPackageSkill().run((raw, 20))

    assert len(result["data"]["activities"]) == 2
    assert result["data"]["validation"] == {
        "valid": True,
        "partial": True,
        "errors": ["选择题必须有唯一且存在于选项中的答案。"],
    }
    assert result["data"]["total_minutes"] == 10
    assert "校验说明" in result["markdown"]


def test_activity_package_drops_items_that_would_exceed_requested_duration() -> None:
    raw = {
        "activities": [
            {"type": "true_false", "duration_minutes": 8, "prompt": "1+1=2", "answer": True},
            {"type": "true_false", "duration_minutes": 8, "prompt": "1+1=3", "answer": False},
        ]
    }

    result = ClassroomActivityPackageSkill().run((json.dumps(raw), 10))

    assert len(result["data"]["activities"]) == 1
    assert result["data"]["discarded_items"][0]["index"] == 1


def test_activity_package_rejects_duplicate_choice_labels() -> None:
    raw = json.dumps(
        {
            "activities": [
                {
                    "type": "multiple_choice",
                    "duration_minutes": 5,
                    "prompt": "重复标签",
                    "options": ["A. 第一项", "A. 第二项"],
                    "answer": "A",
                }
            ]
        }
    )

    with pytest.raises(AppError) as error:
        ClassroomActivityPackageSkill().run((raw, 10))

    assert "选项标签必须唯一" in error.value.message


def test_observation_returns_confirmation_state_for_ambiguous_question_groups() -> None:
    result = ClassroomObservationSkill().run("第一组 8 人选 A、21 人选 B；第二组 8 人选 A、5 人选 C")

    assert result.status == "needs_confirmation"
    assert result.ambiguities
    assert result.counts == {}
    assert result.total == 0


def test_summary_requires_both_explicitly_selected_artifact_types() -> None:
    skill = ClassroomSummarySkill()
    activity = ContextArtifact(
        id=uuid4(),
        type="classroom_activity_package",
        title="活动包",
        content="# 活动包",
        data={"activities": []},
    )

    with pytest.raises(AppError) as error:
        skill.select_inputs((activity,))

    assert error.value.code == "classroom_summary_input_incomplete"
