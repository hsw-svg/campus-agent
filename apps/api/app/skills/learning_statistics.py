from app.agents.teacher.learning_analysis import LearningAnalysisResult, analyze_learning_table
from app.skills.table_parser import ParsedTable


class LearningStatisticsSkill:
    id = "learning_statistics"
    version = "1"
    input_type = "ParsedTable"
    output_type = "LearningAnalysisResult"
    error_codes = ()
    has_side_effects = False
    can_access_workspace = False

    def run(self, value: ParsedTable) -> LearningAnalysisResult:
        return analyze_learning_table(value.text, filename=value.filename)
