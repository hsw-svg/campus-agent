from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.artifacts.models import Artifact
from app.conversations.models import Conversation
from app.core.errors import AppError
from app.courses.context import CourseLearningContext
from app.courses.models import (
    Course,
    CourseChapter,
    CourseChapterProgress,
    StudentCourseProgress,
    StudentCourseWeakPoint,
)


DEFAULT_COURSES: tuple[dict[str, Any], ...] = (
    {
        "template_key": "college-english",
        "name": "大学英语",
        "description": "围绕学术交流、阅读理解与跨文化表达，提升大学阶段英语综合应用能力。",
        "teacher_name": "陈老师",
        "starts_at": datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc),
        "thumbnail_key": "english",
        "category": "语言素养",
        "chapters": (
            ("学术英语入门", "认识大学英语学习目标与常用学术场景", ("学术词汇", "学习策略")),
            ("阅读与信息提取", "掌握主旨、结构与证据定位方法", ("主旨判断", "细节定位")),
            ("听说与观点表达", "在校园情境中清晰表达观点", ("听力笔记", "口语组织")),
            ("跨文化沟通", "理解文化差异并完成得体交流", ("文化语境", "沟通策略")),
        ),
    },
    {
        "template_key": "situation-policy",
        "name": "形势与政策",
        "description": "理解国内外发展形势、公共政策与青年责任，形成理性分析现实问题的能力。",
        "teacher_name": "周老师",
        "starts_at": datetime(2026, 9, 3, 0, 0, tzinfo=timezone.utc),
        "thumbnail_key": "policy",
        "category": "思想政治",
        "chapters": (
            ("时代方位与青年使命", "从时代背景理解大学生的责任与发展方向", ("时代方位", "青年责任")),
            ("高质量发展", "认识经济社会高质量发展的核心内涵", ("新发展理念", "产业升级")),
            ("科技创新与社会进步", "分析科技创新带来的机遇与挑战", ("科技创新", "社会治理")),
            ("全球格局与中国担当", "理解国际格局变化与合作发展", ("全球治理", "国际合作")),
        ),
    },
    {
        "template_key": "advanced-mathematics",
        "name": "高等数学",
        "description": "建立微积分核心概念，培养抽象思维、逻辑推理和数量分析能力。",
        "teacher_name": "王老师",
        "starts_at": datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc),
        "thumbnail_key": "mathematics",
        "category": "数理基础",
        "chapters": (
            ("函数、极限与连续", "理解微积分的语言和极限思想", ("函数性质", "极限", "连续")),
            ("一元函数微分学", "掌握导数及其应用", ("导数", "微分", "中值定理")),
            ("一元函数积分学", "理解积分思想与计算方法", ("不定积分", "定积分")),
            ("多元函数微积分", "将微积分方法拓展到多变量问题", ("偏导数", "重积分")),
        ),
    },
    {
        "template_key": "computer-foundations",
        "name": "大学计算机基础",
        "description": "了解计算机系统、数据表示、网络与程序设计的基础知识。",
        "teacher_name": "刘老师",
        "starts_at": datetime(2026, 9, 4, 0, 0, tzinfo=timezone.utc),
        "thumbnail_key": "computer",
        "category": "数字素养",
        "chapters": (
            ("计算机系统概览", "理解硬件、软件与操作系统的协同关系", ("硬件系统", "操作系统")),
            ("数据表示与处理", "掌握信息在计算机中的表示方式", ("二进制", "编码")),
            ("网络与信息安全", "建立网络使用和数据安全意识", ("计算机网络", "信息安全")),
            ("程序设计思维", "使用分解、抽象和算法解决问题", ("算法", "程序结构")),
        ),
    },
    {
        "template_key": "college-physical-education",
        "name": "大学体育",
        "description": "通过科学锻炼与专项实践，提升体能、运动技能和健康管理意识。",
        "teacher_name": "赵老师",
        "starts_at": datetime(2026, 9, 5, 0, 0, tzinfo=timezone.utc),
        "thumbnail_key": "sports",
        "category": "健康素养",
        "chapters": (
            ("体能评估与训练计划", "了解个人体能并制定安全训练目标", ("体能评估", "训练原则")),
            ("运动技能基础", "掌握热身、动作控制与放松方法", ("动作控制", "运动安全")),
            ("耐力与力量训练", "使用科学方法提升基础体能", ("心肺耐力", "力量训练")),
            ("健康生活方式", "将运动、营养与恢复纳入日常管理", ("营养", "运动恢复")),
        ),
    },
    {
        "template_key": "career-planning",
        "name": "职业生涯规划",
        "description": "通过自我探索、职业认知与行动规划，形成可迭代的大学成长路线。",
        "teacher_name": "孙老师",
        "starts_at": datetime(2026, 9, 6, 0, 0, tzinfo=timezone.utc),
        "thumbnail_key": "career",
        "category": "发展指导",
        "chapters": (
            ("自我认知", "梳理兴趣、能力与价值观", ("兴趣探索", "能力盘点")),
            ("职业世界探索", "理解行业、岗位与能力要求", ("行业研究", "岗位画像")),
            ("目标与路径设计", "将长期方向转化为阶段目标", ("目标管理", "路径规划")),
            ("行动与复盘", "用项目实践验证并迭代规划", ("行动计划", "复盘迭代")),
        ),
    },
)


class StudentCourseService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def ensure_defaults(self, workspace_id: UUID) -> list[dict[str, Any]]:
        existing_keys = set(
            self.session.scalars(
                select(Course.template_key).where(
                    Course.workspace_id == workspace_id,
                    Course.template_key.is_not(None),
                )
            )
        )
        for template in DEFAULT_COURSES:
            if template["template_key"] in existing_keys:
                continue
            course = Course(
                workspace_id=workspace_id,
                template_key=template["template_key"],
                name=template["name"],
                description=template["description"],
                teacher_name=template["teacher_name"],
                starts_at=template["starts_at"],
                thumbnail_key=template["thumbnail_key"],
                category=template["category"],
            )
            self.session.add(course)
            self.session.flush()
            for position, (title, summary, knowledge_points) in enumerate(template["chapters"], start=1):
                self.session.add(
                    CourseChapter(
                        course_id=course.id,
                        title=title,
                        summary=summary,
                        position=position,
                        estimated_minutes=45,
                        knowledge_points=list(knowledge_points),
                    )
                )
        self.session.commit()
        return self.list_summaries(workspace_id)

    def list_summaries(self, workspace_id: UUID) -> list[dict[str, Any]]:
        courses = list(
            self.session.scalars(
                select(Course)
                .where(Course.workspace_id == workspace_id)
                .order_by(Course.starts_at.asc().nullslast(), Course.created_at.asc())
            )
        )
        return [self._summary(workspace_id, course) for course in courses]

    def get_detail(self, workspace_id: UUID, course_id: UUID) -> dict[str, Any]:
        course = self._owned_course(workspace_id, course_id)
        chapters = self._chapters(course.id)
        progress = self._progress(workspace_id, course.id)
        completed = self._completed_chapter_ids(progress)
        summary = self._summary(workspace_id, course, chapters=chapters, progress=progress, completed=completed)
        chapter_items = [
            {
                "id": chapter.id,
                "title": chapter.title,
                "summary": chapter.summary,
                "position": chapter.position,
                "estimated_minutes": chapter.estimated_minutes,
                "knowledge_points": chapter.knowledge_points,
                "completed": chapter.id in completed,
                "current": progress is not None and progress.current_chapter_id == chapter.id,
            }
            for chapter in chapters
        ]
        weak_points = []
        if progress is not None:
            weak_points = [
                {
                    "id": item.id,
                    "chapter_id": item.chapter_id,
                    "name": item.name,
                    "recommendation": item.recommendation,
                }
                for item in self.session.scalars(
                    select(StudentCourseWeakPoint)
                    .where(StudentCourseWeakPoint.course_progress_id == progress.id)
                    .order_by(StudentCourseWeakPoint.updated_at.desc())
                )
            ]
        return {
            **summary,
            "chapters": chapter_items,
            "current_chapter_id": progress.current_chapter_id if progress else None,
            "weak_points": weak_points,
        }

    def get_learning_context(
        self,
        workspace_id: UUID,
        course_id: UUID,
        chapter_id: UUID | None,
    ) -> CourseLearningContext:
        course = self._owned_course(workspace_id, course_id)
        chapter = (
            self._owned_chapter(workspace_id, course_id, chapter_id)
            if chapter_id is not None
            else None
        )
        return CourseLearningContext(
            course_id=str(course.id),
            course_name=course.name,
            description=course.description,
            category=course.category,
            teacher_name=course.teacher_name,
            chapter_id=str(chapter.id) if chapter is not None else None,
            chapter_title=chapter.title if chapter is not None else None,
            chapter_summary=chapter.summary if chapter is not None else None,
            knowledge_points=tuple(str(item) for item in (chapter.knowledge_points or ()))
            if chapter is not None
            else (),
        )

    def start_course(self, workspace_id: UUID, course_id: UUID) -> dict[str, Any]:
        course = self._owned_course(workspace_id, course_id)
        chapters = self._chapters(course.id)
        now = datetime.now(timezone.utc)
        progress = self._progress(workspace_id, course.id)
        if progress is None:
            progress = StudentCourseProgress(
                workspace_id=workspace_id,
                course_id=course.id,
                started_at=now,
                last_studied_at=now,
                current_chapter_id=chapters[0].id if chapters else None,
            )
            self.session.add(progress)
            self.session.flush()
        else:
            progress.last_studied_at = now
        if progress.current_chapter_id is not None:
            self._ensure_chapter_progress(progress.id, progress.current_chapter_id, now)
        self.session.commit()
        return self.get_detail(workspace_id, course_id)

    def start_chapter(self, workspace_id: UUID, course_id: UUID, chapter_id: UUID) -> dict[str, Any]:
        self._owned_chapter(workspace_id, course_id, chapter_id)
        self.start_course(workspace_id, course_id)
        progress = self._required_progress(workspace_id, course_id)
        now = datetime.now(timezone.utc)
        progress.current_chapter_id = chapter_id
        progress.last_studied_at = now
        self._ensure_chapter_progress(progress.id, chapter_id, now)
        self.session.commit()
        return self.get_detail(workspace_id, course_id)

    def complete_chapter(self, workspace_id: UUID, course_id: UUID, chapter_id: UUID) -> dict[str, Any]:
        self._owned_chapter(workspace_id, course_id, chapter_id)
        self.start_chapter(workspace_id, course_id, chapter_id)
        progress = self._required_progress(workspace_id, course_id)
        now = datetime.now(timezone.utc)
        chapter_progress = self._ensure_chapter_progress(progress.id, chapter_id, now)
        chapter_progress.completed_at = chapter_progress.completed_at or now
        progress.last_studied_at = now
        self._refresh_weak_points(progress, chapter_id)

        completed = self._completed_chapter_ids(progress)
        chapters = self._chapters(course_id)
        next_chapter = next((item for item in chapters if item.id not in completed), None)
        progress.current_chapter_id = next_chapter.id if next_chapter else chapter_id
        if next_chapter is not None:
            self._ensure_chapter_progress(progress.id, next_chapter.id, now)
        self.session.commit()
        return self.get_detail(workspace_id, course_id)

    def get_owned_chapter(self, workspace_id: UUID, course_id: UUID, chapter_id: UUID) -> CourseChapter:
        return self._owned_chapter(workspace_id, course_id, chapter_id)

    def _summary(
        self,
        workspace_id: UUID,
        course: Course,
        *,
        chapters: list[CourseChapter] | None = None,
        progress: StudentCourseProgress | None = None,
        completed: set[UUID] | None = None,
    ) -> dict[str, Any]:
        chapters = chapters if chapters is not None else self._chapters(course.id)
        progress = progress if progress is not None else self._progress(workspace_id, course.id)
        completed = completed if completed is not None else self._completed_chapter_ids(progress)
        chapter_count = len(chapters)
        completed_count = len(completed)
        return {
            "id": course.id,
            "name": course.name,
            "description": course.description,
            "teacher_name": course.teacher_name,
            "starts_at": course.starts_at,
            "thumbnail_key": course.thumbnail_key,
            "category": course.category,
            "chapter_count": chapter_count,
            "completed_chapter_count": completed_count,
            "progress_percent": round(completed_count * 100 / chapter_count) if chapter_count else 0,
            "started": progress is not None,
            "last_studied_at": progress.last_studied_at if progress else None,
            "created_at": course.created_at,
            "updated_at": course.updated_at,
        }

    def _owned_course(self, workspace_id: UUID, course_id: UUID) -> Course:
        course = self.session.scalar(
            select(Course).where(Course.id == course_id, Course.workspace_id == workspace_id)
        )
        if course is None:
            raise AppError(code="course_not_found", message="Course was not found.", status_code=404)
        return course

    def _owned_chapter(self, workspace_id: UUID, course_id: UUID, chapter_id: UUID) -> CourseChapter:
        self._owned_course(workspace_id, course_id)
        chapter = self.session.scalar(
            select(CourseChapter).where(
                CourseChapter.id == chapter_id,
                CourseChapter.course_id == course_id,
            )
        )
        if chapter is None:
            raise AppError(code="course_chapter_not_found", message="Course chapter was not found.", status_code=404)
        return chapter

    def _chapters(self, course_id: UUID) -> list[CourseChapter]:
        return list(
            self.session.scalars(
                select(CourseChapter)
                .where(CourseChapter.course_id == course_id)
                .order_by(CourseChapter.position.asc())
            )
        )

    def _progress(self, workspace_id: UUID, course_id: UUID) -> StudentCourseProgress | None:
        return self.session.scalar(
            select(StudentCourseProgress).where(
                StudentCourseProgress.workspace_id == workspace_id,
                StudentCourseProgress.course_id == course_id,
            )
        )

    def _required_progress(self, workspace_id: UUID, course_id: UUID) -> StudentCourseProgress:
        progress = self._progress(workspace_id, course_id)
        if progress is None:
            raise RuntimeError("Course progress was not created.")
        return progress

    def _completed_chapter_ids(self, progress: StudentCourseProgress | None) -> set[UUID]:
        if progress is None:
            return set()
        return set(
            self.session.scalars(
                select(CourseChapterProgress.chapter_id).where(
                    CourseChapterProgress.course_progress_id == progress.id,
                    CourseChapterProgress.completed_at.is_not(None),
                )
            )
        )

    def _ensure_chapter_progress(
        self,
        course_progress_id: UUID,
        chapter_id: UUID,
        now: datetime,
    ) -> CourseChapterProgress:
        item = self.session.scalar(
            select(CourseChapterProgress).where(
                CourseChapterProgress.course_progress_id == course_progress_id,
                CourseChapterProgress.chapter_id == chapter_id,
            )
        )
        if item is None:
            item = CourseChapterProgress(
                course_progress_id=course_progress_id,
                chapter_id=chapter_id,
                started_at=now,
            )
            self.session.add(item)
            self.session.flush()
        return item

    def _refresh_weak_points(self, progress: StudentCourseProgress, chapter_id: UUID) -> None:
        self.session.execute(
            delete(StudentCourseWeakPoint).where(
                StudentCourseWeakPoint.course_progress_id == progress.id,
                StudentCourseWeakPoint.chapter_id == chapter_id,
            )
        )
        artifacts = list(
            self.session.scalars(
                select(Artifact)
                .join(Conversation, Conversation.id == Artifact.conversation_id)
                .where(
                    Artifact.workspace_id == progress.workspace_id,
                    Artifact.type == "personal_tutor",
                    Conversation.workspace_id == progress.workspace_id,
                    Conversation.course_id == progress.course_id,
                    Conversation.chapter_id == chapter_id,
                )
                .order_by(Artifact.created_at.desc())
            )
        )
        seen: set[str] = set()
        for artifact in artifacts:
            mistakes = artifact.data.get("mistakes") if isinstance(artifact.data, dict) else None
            practice = artifact.data.get("practice") if isinstance(artifact.data, dict) else None
            if not isinstance(mistakes, list):
                continue
            recommendations = [item for item in practice if isinstance(item, str)] if isinstance(practice, list) else []
            for index, mistake in enumerate(mistakes):
                if not isinstance(mistake, str) or not mistake.strip() or mistake.strip() in seen:
                    continue
                name = mistake.strip()[:200]
                seen.add(name)
                recommendation = (
                    recommendations[index]
                    if index < len(recommendations)
                    else "回到本节 AI 学习工作台，结合例题复习并完成一次针对性练习。"
                )
                self.session.add(
                    StudentCourseWeakPoint(
                        course_progress_id=progress.id,
                        chapter_id=chapter_id,
                        name=name,
                        recommendation=recommendation,
                        evidence_artifact_id=artifact.id,
                    )
                )
                if len(seen) >= 5:
                    return
