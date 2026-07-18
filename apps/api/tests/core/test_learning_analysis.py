from app.agents.teacher.learning_analysis import analyze_learning_table


TABLE = """匿名编号 | 课程 | 课程章节范围 | 2026-07-01签到 | 2026-07-03签到 | 课堂积极性评分 | 作业1_Python基础 | 作业2_条件与循环 | 作业3_函数与模块 | 满分
A01 | Python程序设计 | 基础、条件、函数 | 签到 | 签到 | 5 | 90 | 80 | 70 | 100
A02 | Python程序设计 | 基础、条件、函数 | 迟到 | 缺勤 | 3 | 70 | 60 | 50 | 100
A03 | Python程序设计 | 基础、条件、函数 | 签到 | 签到 | 4 | 80 | 70 | 60 | 100
"""


def test_learning_analysis_returns_class_level_deterministic_statistics() -> None:
    result = analyze_learning_table(TABLE, filename="python_scores.csv")

    assert result.data["scope"] == "class"
    assert result.data["student_count"] == 3
    assert result.data["attendance"]["sessions"] == 2
    assert result.data["attendance"]["present"] == 4
    assert result.data["attendance"]["late"] == 1
    assert result.data["attendance"]["absent"] == 1
    assert result.data["attendance"]["rate"] == 5 / 6
    assert result.data["activity"]["average"] == 4.0
    assert result.data["assignments"][0]["average"] == 80.0
    assert result.data["assignments"][2]["average"] == 60.0
    assert result.data["weak_points"][0]["name"] == "作业3_函数与模块"
    assert result.data["course_profile"]["course"] == "Python程序设计"
    assert result.data["guidance"]
    assert "A01" not in result.markdown
    assert "学情标签" not in result.markdown
    assert "student_profiles" not in result.data


def test_learning_analysis_exposes_relationships_and_iteration_strategy() -> None:
    table = TABLE.replace("满分", "期末成绩 | 满分").replace(
        "90 | 80 | 70 | 100", "90 | 80 | 70 | 88 | 100",
    ).replace(
        "70 | 60 | 50 | 100", "70 | 60 | 50 | 55 | 100",
    ).replace(
        "80 | 70 | 60 | 100", "80 | 70 | 60 | 68 | 100",
    )

    result = analyze_learning_table(table, filename="python_scores.csv")

    relationships = result.data["relationships"]
    assert relationships["final_score_field"] == "期末成绩"
    assert relationships["correlations"][1]["coefficient"] is not None
    assert relationships["attendance_bands"]
    assert result.data["teaching_diagnosis"]
    assert result.data["iteration_strategy"]


def test_learning_analysis_rejects_table_without_anonymous_identifier() -> None:
    result = analyze_learning_table(
        "姓名 | 作业1 | 课堂积极性评分\n张三 | 80 | 4\n",
        filename="scores.csv",
    )

    assert result.data["validation"]["valid"] is False
    assert "anonymous_id_required" in result.data["validation"]["errors"]
