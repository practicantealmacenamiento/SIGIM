from __future__ import annotations

from types import SimpleNamespace
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from app.application.commands import (
    AddTableRowCommand,
    TableCellInput,
    UpdateTableRowCommand,
)
from app.application.tabular import TabularFormService
from app.domain.entities import Answer, Question
from app.domain.repositories import (
    ActorRepository,
    AnswerRepository,
    ChoiceRepository,
    QuestionRepository,
    SubmissionRepository,
)


class FakeAnswerRepository(AnswerRepository):
    def __init__(self) -> None:
        self._answers: List[Answer] = []

    def save(self, answer: Answer) -> Answer:
        self._answers = [a for a in self._answers if a.id != answer.id]
        self._answers.append(answer)
        return answer

    def get(self, id: UUID) -> Optional[Answer]:
        return next((a for a in self._answers if a.id == id), None)

    def delete(self, id: UUID) -> None:
        self._answers = [a for a in self._answers if a.id != id]

    def list_by_user(self, user_id, *, limit: Optional[int] = None) -> List[Answer]:
        raise NotImplementedError

    def list_by_submission(self, submission_id: UUID) -> List[Answer]:
        return [a for a in self._answers if a.submission_id == submission_id]

    def list_by_question(self, question_id: UUID) -> List[Answer]:
        return [a for a in self._answers if a.question_id == question_id]

    def clear_for_question(self, *, submission_id: UUID, question_id: UUID) -> int:
        raise NotImplementedError

    def delete_after_question(self, *, submission_id: UUID, question_id: UUID) -> int:
        raise NotImplementedError


class FakeSubmissionRepository(SubmissionRepository):
    def __init__(self, submission_ids: List[UUID]) -> None:
        self._data: Dict[UUID, SimpleNamespace] = {
            sid: SimpleNamespace(id=sid) for sid in submission_ids
        }

    def get(self, id: UUID):
        return self._data.get(id)

    def save(self, submission):
        raise NotImplementedError

    def save_partial_updates(self, id: UUID, **fields) -> None:
        raise NotImplementedError

    def list_for_api(self, params):
        raise NotImplementedError

    def ensure_regulador_on_create(self, obj) -> None:
        raise NotImplementedError

    def detail_queryset(self):
        raise NotImplementedError

    def get_detail(self, id: UUID):
        raise NotImplementedError

    def history_aggregate(self, *, fecha_desde=None, fecha_hasta=None):
        raise NotImplementedError

    def get_by_ids(self, ids):
        raise NotImplementedError


class FakeQuestionRepository(QuestionRepository):
    def __init__(self, mapping: Dict[UUID, Question]) -> None:
        self._mapping = mapping

    def get(self, id: UUID) -> Optional[Question]:
        return self._mapping.get(id)

    def list_by_questionnaire(self, questionnaire_id: UUID):
        raise NotImplementedError

    def next_in_questionnaire(self, current_question_id: UUID) -> Optional[UUID]:
        raise NotImplementedError

    def find_next_by_order(self, questionnaire_id: UUID, order: int) -> Optional[UUID]:
        raise NotImplementedError


class FakeChoiceRepository(ChoiceRepository):
    def get(self, id: UUID):
        return None


class FakeActorRepository(ActorRepository):
    def __init__(self, actors: Dict[UUID, SimpleNamespace]) -> None:
        self._actors = actors

    def get(self, id: UUID):
        return self._actors.get(id)

    def list_by_type(self, tipo: str, *, search: Optional[str] = None, limit: int = 50):
        raise NotImplementedError


class FakeStorage:
    def save(self, folder: str, file_obj):
        return f"{folder}/fake-upload"


def make_question(*, semantic_tag: Optional[str] = None, order: int = 1) -> Question:
    return Question(
        id=uuid4(),
        text="Pregunta",
        type="text",
        required=False,
        order=order,
        choices=None,
        semantic_tag=semantic_tag,
        file_mode=None,
    )


def test_add_and_update_rows_include_actor_details():
    submission_id = uuid4()
    answers_repo = FakeAnswerRepository()

    text_question = make_question(order=1)
    actor_question = make_question(semantic_tag="proveedor", order=2)

    actor_id = uuid4()
    actor_repo = FakeActorRepository({
        actor_id: SimpleNamespace(id=actor_id, nombre="Proveedor Uno", documento="900123"),
    })

    service = TabularFormService(
        answer_repo=answers_repo,
        submission_repo=FakeSubmissionRepository([submission_id]),
        question_repo=FakeQuestionRepository({
            text_question.id: text_question,
            actor_question.id: actor_question,
        }),
        choice_repo=FakeChoiceRepository(),
        actor_repo=actor_repo,
        storage=FakeStorage(),
    )

    result = service.add_row(
        AddTableRowCommand(
            submission_id=submission_id,
            row_index=None,
            cells=[
                TableCellInput(question_id=text_question.id, answer_text="ABC123"),
                TableCellInput(question_id=actor_question.id, actor_id=actor_id),
            ],
        )
    )

    assert result.row_index == 1
    assert result.values[str(text_question.id)]["answer_text"] == "ABC123"
    actor_cell = result.values[str(actor_question.id)]
    assert actor_cell["actor_id"] == str(actor_id)
    assert actor_cell["actor_name"] == "Proveedor Uno"
    assert actor_cell["actor_document"] == "900123"

    rows = service.list_rows(submission_id)
    assert len(rows) == 1
    actor_list_cell = rows[0].values[str(actor_question.id)]
    assert actor_list_cell["actor_name"] == "Proveedor Uno"

    service.update_row(
        UpdateTableRowCommand(
            submission_id=submission_id,
            row_index=result.row_index,
            cells=[
                TableCellInput(question_id=text_question.id, answer_text="XYZ999"),
                TableCellInput(question_id=actor_question.id, actor_id=actor_id),
            ],
        )
    )

    rows_after = service.list_rows(submission_id)
    assert rows_after[0].values[str(text_question.id)]["answer_text"] == "XYZ999"
    assert len(answers_repo.list_by_submission(submission_id)) == 2
