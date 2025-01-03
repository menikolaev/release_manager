import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dateutil.parser import parse
from git import Repo, GitCommandError, Git
from pydantic import BaseModel

if TYPE_CHECKING:
    from apps.adapters.gitlab import GitlabApi


class BuildCreateError(Exception):
    pass


class BuildRequest(BaseModel):
    project_name: str
    mrs_order: list[str]
    major_version: int
    sprint_number: int


class BuildCreateService:
    ENABLED_MR_STATUS = 'can_be_merged'

    def __init__(self, build_api: 'GitlabApi'):
        self.build_api = build_api

    def create_build(self, build_request: BuildRequest) -> str:
        # Добываем проект по названию
        project = self.build_api.get_project_by_name(name=build_request.project_name)

        # добываем все MR'ы этого проекта
        merge_requests = self.build_api.get_ready_merge_requests(project_id=project['id'])
        print(merge_requests)

        available_mrs = self._get_available_mrs(merge_requests=merge_requests, build_request=build_request)
        filtered_mrs = self._filter_mrs(available_mrs=available_mrs)
        # сортируем MR'ы по возрастанию даты создания (это потом надо улучшить с учетом цепочек MR'ов)
        sorted_mrs = sorted(filtered_mrs, key=lambda x: parse(x['created_at']))

        # Создаем новую ветку от мастера с названием build-v1.2.1 (<major_version>.<sprint_number>.<sprint_build>)
        # Нужно загрузить последнюю ветку с заданным sem_ver, если ее нет, то создать первую, если есть, то создать n+1
        # версию
        build_branch_name = self._get_new_build_branch_name(project=project, build_request=build_request)
        self._create_new_build_branch(project=project, build_branch_name=build_branch_name)

        self._make_build(project=project, sorted_mrs=sorted_mrs, build_branch_name=build_branch_name)

        return f'Build {build_branch_name} successfully created'

    def _get_available_mrs(self, merge_requests: list[dict[Any, Any]], build_request: BuildRequest):
        if not build_request.mrs_order:
            return []

        available_mrs = []
        for mr in merge_requests:
            for available_mr in build_request.mrs_order:
                # FIXME: возможен вариант, когда TEST-1 и TEST-10 пройдут эту проверку
                if mr['source_branch'].startswith(available_mr):
                    available_mrs.append(mr)

        return available_mrs

    def _filter_mrs(self, available_mrs: list[dict[Any, Any]]) -> list[dict[Any, Any]]:
        filtered_mrs = []
        fails = []
        for mr in available_mrs:
            if not mr['blocking_discussions_resolved']:
                fails.append(f'MR {mr["source_branch"]} cannot be merged due to discussions are not resolved')
                continue

            if mr['has_conflicts']:
                fails.append(
                    f'MR {mr["source_branch"]} cannot be merged due to conflicts with target branch {mr["target_branch"]}'
                )
                continue

            if mr['merge_status'] != self.ENABLED_MR_STATUS:
                fails.append(f'MR {mr["source_branch"]} cannot be merged, current MR status {mr["merge_status"]}')
                continue

            filtered_mrs.append(mr)

        if fails:
            raise BuildCreateError(fails)

        return filtered_mrs

    def _get_new_build_branch_name(self, project: dict[Any, Any], build_request: BuildRequest) -> str:
        sprint_build_number = 1
        build_branches = self.build_api.get_build_branches(
            project_id=project['id'],
            major_version=build_request.major_version,
            sprint_number=build_request.sprint_number,
        )

        if build_branches:
            sorted_build_branches = sorted(build_branches, key=lambda x: int(x['name'].split('.')[-1]), reverse=True)
            last_branch = sorted_build_branches[0]
            last_sprint_build_number = int(last_branch['name'].split('.')[-1])
            sprint_build_number = last_sprint_build_number + 1

        return f'build-v{build_request.major_version}.{build_request.sprint_number}.{sprint_build_number}'

    def _create_new_build_branch(self, project: dict[Any, Any], build_branch_name: str) -> None:
        raw_result = self.build_api.create_build_branch(project_id=project['id'], build_branch_name=build_branch_name)
        if raw_result.status_code != 201:
            result = raw_result.json()
            raise BuildCreateError(f'Branch with name {build_branch_name} was not created. Message: {result}')

    def _make_build(self, project: dict[Any, Any], sorted_mrs: list[dict[Any, Any]], build_branch_name: str) -> None:
        # Создаем дерикторию, где будем мержить ветки
        repo_temp_path = Path(f'/tmp/repos/{project["path"]}')
        repo_temp_path.mkdir(parents=True, exist_ok=True)

        # Клонируем репозиторий себе в локальную папку
        try:
            repo = Repo.clone_from(project['ssh_url_to_repo'], repo_temp_path)
        except GitCommandError:
            shutil.rmtree(str(repo_temp_path))
            repo = Repo.clone_from(project['ssh_url_to_repo'], repo_temp_path)

        # Скачиваем ветку текущего нового билда
        _git = repo.git
        _git.checkout(build_branch_name)
        _git.pull()

        # Сливаем ветки в ветку билда по порядку
        for mr in sorted_mrs:
            try:
                self._merge_mr(git=_git, mr=mr, build_branch_name=build_branch_name)
            except GitCommandError as exc:
                raise BuildCreateError(f'Failed to merge MR {mr["source_branch"]} into build due to: {exc}')

        # Заливаем все изменения в репозиторий
        repo.remotes.origin.push(refspec=f'{build_branch_name}:{build_branch_name}')

        # Чистим за собой в локальной папке
        shutil.rmtree(str(repo_temp_path))

    def _merge_mr(self, git: Git, mr: dict[Any, Any], build_branch_name: str):
        git.checkout(mr['source_branch'])
        git.pull()
        git.checkout(build_branch_name)
        git.merge(mr['source_branch'])
