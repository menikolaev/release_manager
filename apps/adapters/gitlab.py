from typing import TYPE_CHECKING, Any, Optional

import requests

if TYPE_CHECKING:
    from config.settings import Config


class GitlabApi:
    def __init__(self, settings: 'Config'):
        self.settings = settings
        self.request_headers = {'PRIVATE-TOKEN': settings.gitlab_token.get_secret_value()}

    def get_project_by_name(self, name: str) -> dict[Any, Any]:
        url = '{gitlab_host}/api/v4/projects?simple=yes&visibility=private&search={project_name}&min_access_level=30'

        raw_result = requests.get(
            url.format(gitlab_host=self.settings.gitlab_host, project_name=name), headers=self.request_headers,
        )
        result = raw_result.json()

        return result[0]

    def get_ready_merge_requests(self, project_id: int) -> list[dict[Any, Any]]:
        url = '{gitlab_host}/api/v4/projects/{project_id}/merge_requests?state=opened&wip=no'

        raw_result = requests.get(
            url.format(gitlab_host=self.settings.gitlab_host, project_id=project_id),
            headers=self.request_headers,
        )
        return raw_result.json()

    def get_build_branches(self, project_id: int, major_version: int, sprint_number: int) -> list[dict[Any, Any]]:
        url = '{gitlab_host}/api/v4/projects/{project_id}/repository/branches?search=^build-v{major_version}.{sprint_number}'
        raw_result = requests.get(
            url.format(
                gitlab_host=self.settings.gitlab_host,
                project_id=project_id,
                major_version=major_version,
                sprint_number=sprint_number,
            ),
            headers=self.request_headers,
        )
        return raw_result.json()

    def create_build_branch(
            self,
            project_id: int,
            build_branch_name: str,
            ref_branch: Optional[str] = None,
    ) -> requests.Response:
        url = '{gitlab_host}/api/v4/projects/{project_id}/repository/branches?branch={build_branch_name}&ref={ref_branch}'
        return requests.post(
            url.format(
                gitlab_host=self.settings.gitlab_host,
                project_id=project_id,
                build_branch_name=build_branch_name,
                ref_branch=ref_branch or self.settings.ref_branch,
            ),
            headers=self.request_headers,
        )
