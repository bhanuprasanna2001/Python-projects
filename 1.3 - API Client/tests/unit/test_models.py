"""Unit tests for Pydantic models."""

from __future__ import annotations

from datetime import datetime

from github_client.models import (
    Commit,
    Gist,
    Issue,
    Organization,
    PullRequest,
    Repository,
    SimpleUser,
    User,
)


class TestUserModel:
    """Tests for the User model."""

    def test_parse_minimal_user(self):
        """Test parsing a minimal user response."""
        data = {
            "login": "octocat",
            "id": 1,
            "node_id": "MDQ6VXNlcjE=",
            "avatar_url": "https://github.com/images/error/octocat_happy.gif",
            "url": "https://api.github.com/users/octocat",
            "html_url": "https://github.com/octocat",
            "followers_url": "https://api.github.com/users/octocat/followers",
            "following_url": "https://api.github.com/users/octocat/following",
            "gists_url": "https://api.github.com/users/octocat/gists",
            "starred_url": "https://api.github.com/users/octocat/starred",
            "repos_url": "https://api.github.com/users/octocat/repos",
            "events_url": "https://api.github.com/users/octocat/events",
            "received_events_url": "https://api.github.com/users/octocat/received_events",
            "type": "User",
        }
        user = User.model_validate(data)

        assert user.login == "octocat"
        assert user.id == 1
        assert user.type == "User"
        assert user.name is None
        assert user.public_repos is None

    def test_parse_full_user(self, sample_user_response):
        """Test parsing a full user response."""
        user = User.model_validate(sample_user_response)

        assert user.login == "octocat"
        assert user.name == "The Octocat"
        assert user.company == "@github"
        assert user.public_repos == 8
        assert user.followers == 20
        assert isinstance(user.created_at, datetime)

    def test_user_str(self, sample_user_response):
        """Test User string representation."""
        user = User.model_validate(sample_user_response)
        assert str(user) == "User(octocat)"


class TestSimpleUserModel:
    """Tests for the SimpleUser model."""

    def test_parse_simple_user(self):
        """Test parsing a simple user reference."""
        data = {
            "login": "octocat",
            "id": 1,
            "node_id": "MDQ6VXNlcjE=",
            "avatar_url": "https://github.com/images/error/octocat_happy.gif",
            "url": "https://api.github.com/users/octocat",
            "html_url": "https://github.com/octocat",
            "type": "User",
        }
        user = SimpleUser.model_validate(data)

        assert user.login == "octocat"
        assert user.id == 1
        assert user.site_admin is False


class TestRepositoryModel:
    """Tests for the Repository model."""

    def test_parse_repository(self, sample_repo_response):
        """Test parsing a repository response."""
        repo = Repository.model_validate(sample_repo_response)

        assert repo.name == "Hello-World"
        assert repo.full_name == "octocat/Hello-World"
        assert repo.private is False
        assert repo.owner.login == "octocat"
        assert repo.stargazers_count == 80000
        assert repo.language == "Python"
        assert repo.license is not None
        assert repo.license.key == "mit"

    def test_repository_stars_alias(self, sample_repo_response):
        """Test the stars property alias."""
        repo = Repository.model_validate(sample_repo_response)
        assert repo.stars == repo.stargazers_count

    def test_repository_str(self, sample_repo_response):
        """Test Repository string representation."""
        repo = Repository.model_validate(sample_repo_response)
        assert str(repo) == "Repository(octocat/Hello-World)"

    def test_repository_with_topics(self, sample_repo_response):
        """Test repository with topics."""
        repo = Repository.model_validate(sample_repo_response)
        assert "octocat" in repo.topics
        assert "api" in repo.topics


class TestIssueModel:
    """Tests for the Issue model."""

    def test_parse_issue(self, sample_issue_response):
        """Test parsing an issue response."""
        issue = Issue.model_validate(sample_issue_response)

        assert issue.number == 1347
        assert issue.title == "Found a bug"
        assert issue.state == "open"
        assert issue.user is not None
        assert issue.user.login == "octocat"
        assert len(issue.labels) == 1
        assert issue.labels[0].name == "bug"

    def test_issue_is_not_pull_request(self, sample_issue_response):
        """Test issue without PR data."""
        issue = Issue.model_validate(sample_issue_response)
        assert issue.is_pull_request is False

    def test_issue_str(self, sample_issue_response):
        """Test Issue string representation."""
        issue = Issue.model_validate(sample_issue_response)
        assert "#1347" in str(issue)
        assert "Found a bug" in str(issue)


class TestPullRequestModel:
    """Tests for the PullRequest model."""

    def test_parse_pull_request(self):
        """Test parsing a pull request response."""
        data = {
            "id": 1,
            "node_id": "MDExOlB1bGxSZXF1ZXN0MQ==",
            "url": "https://api.github.com/repos/octocat/Hello-World/pulls/1347",
            "html_url": "https://github.com/octocat/Hello-World/pull/1347",
            "diff_url": "https://github.com/octocat/Hello-World/pull/1347.diff",
            "patch_url": "https://github.com/octocat/Hello-World/pull/1347.patch",
            "issue_url": "https://api.github.com/repos/octocat/Hello-World/issues/1347",
            "number": 1347,
            "state": "open",
            "locked": False,
            "title": "Amazing new feature",
            "body": "Please pull these changes",
            "head": {"ref": "feature", "sha": "abc123"},
            "base": {"ref": "main", "sha": "def456"},
            "merged": False,
        }
        pr = PullRequest.model_validate(data)

        assert pr.number == 1347
        assert pr.title == "Amazing new feature"
        assert pr.state == "open"
        assert pr.merged is False

    def test_pull_request_str(self):
        """Test PullRequest string representation."""
        data = {
            "id": 1,
            "node_id": "MDExOlB1bGxSZXF1ZXN0MQ==",
            "url": "https://api.github.com/repos/octocat/Hello-World/pulls/1",
            "html_url": "https://github.com/octocat/Hello-World/pull/1",
            "diff_url": "https://github.com/octocat/Hello-World/pull/1.diff",
            "patch_url": "https://github.com/octocat/Hello-World/pull/1.patch",
            "issue_url": "https://api.github.com/repos/octocat/Hello-World/issues/1",
            "number": 1,
            "state": "open",
            "locked": False,
            "title": "Fix bug",
            "head": {"ref": "fix", "sha": "abc"},
            "base": {"ref": "main", "sha": "def"},
        }
        pr = PullRequest.model_validate(data)
        assert "#1" in str(pr)
        assert "Fix bug" in str(pr)


class TestOrganizationModel:
    """Tests for the Organization model."""

    def test_parse_organization(self):
        """Test parsing an organization response."""
        data = {
            "login": "github",
            "id": 1,
            "node_id": "MDEyOk9yZ2FuaXphdGlvbjE=",
            "url": "https://api.github.com/orgs/github",
            "html_url": "https://github.com/github",
            "avatar_url": "https://github.com/images/error/octocat_happy.gif",
            "description": "A great organization",
            "name": "GitHub",
            "public_repos": 100,
            "followers": 1000,
        }
        org = Organization.model_validate(data)

        assert org.login == "github"
        assert org.name == "GitHub"
        assert org.public_repos == 100

    def test_organization_str(self):
        """Test Organization string representation."""
        data = {
            "login": "microsoft",
            "id": 1,
            "node_id": "MDEyOk9yZ2FuaXphdGlvbjE=",
            "url": "https://api.github.com/orgs/microsoft",
            "html_url": "https://github.com/microsoft",
            "avatar_url": "https://github.com/images/error/octocat_happy.gif",
        }
        org = Organization.model_validate(data)
        assert str(org) == "Organization(microsoft)"


class TestGistModel:
    """Tests for the Gist model."""

    def test_parse_gist(self):
        """Test parsing a gist response."""
        data = {
            "id": "aa5a315d61ae9438b18d",
            "node_id": "MDQ6R2lzdGFhNWEzMTVkNjFhZTk0MzhiMThk",
            "url": "https://api.github.com/gists/aa5a315d61ae9438b18d",
            "html_url": "https://gist.github.com/aa5a315d61ae9438b18d",
            "git_pull_url": "https://gist.github.com/aa5a315d61ae9438b18d.git",
            "git_push_url": "https://gist.github.com/aa5a315d61ae9438b18d.git",
            "commits_url": "https://api.github.com/gists/aa5a315d61ae9438b18d/commits",
            "forks_url": "https://api.github.com/gists/aa5a315d61ae9438b18d/forks",
            "public": True,
            "description": "Hello World",
            "files": {
                "hello.py": {
                    "filename": "hello.py",
                    "type": "application/x-python",
                    "language": "Python",
                    "raw_url": "https://gist.githubusercontent.com/raw/hello.py",
                    "size": 23,
                }
            },
        }
        gist = Gist.model_validate(data)

        assert gist.id == "aa5a315d61ae9438b18d"
        assert gist.public is True
        assert "hello.py" in gist.files
        assert gist.files["hello.py"].language == "Python"


class TestCommitModel:
    """Tests for the Commit model."""

    def test_parse_commit(self):
        """Test parsing a commit response."""
        data = {
            "sha": "abc123def456",
            "node_id": "MDY6Q29tbWl0YWJjMTIzZGVmNDU2",
            "url": "https://api.github.com/repos/octocat/Hello-World/commits/abc123def456",
            "html_url": "https://github.com/octocat/Hello-World/commit/abc123def456",
            "comments_url": "https://api.github.com/repos/octocat/Hello-World/commits/abc123def456/comments",
            "commit": {
                "author": {
                    "name": "Monalisa Octocat",
                    "email": "octocat@github.com",
                    "date": "2011-04-14T16:00:49Z",
                },
                "committer": {
                    "name": "Monalisa Octocat",
                    "email": "octocat@github.com",
                    "date": "2011-04-14T16:00:49Z",
                },
                "message": "Fix all the bugs",
                "tree": {"sha": "tree123", "url": "https://api.github.com/trees/tree123"},
                "url": "https://api.github.com/commits/abc123def456",
            },
            "parents": [],
        }
        commit = Commit.model_validate(data)

        assert commit.sha == "abc123def456"
        assert commit.commit.message == "Fix all the bugs"
        assert commit.commit.author.name == "Monalisa Octocat"

    def test_commit_str(self):
        """Test Commit string representation."""
        data = {
            "sha": "abc123def456789",
            "node_id": "MDY6Q29tbWl0",
            "url": "https://api.github.com/repos/octocat/Hello-World/commits/abc123",
            "html_url": "https://github.com/octocat/Hello-World/commit/abc123",
            "comments_url": "https://api.github.com/commits/abc123/comments",
            "commit": {
                "author": {"name": "Test", "email": "test@test.com"},
                "committer": {"name": "Test", "email": "test@test.com"},
                "message": "Initial commit\n\nWith a longer description",
                "tree": {"sha": "tree", "url": "https://api.github.com/trees/tree"},
                "url": "https://api.github.com/commits/abc123",
            },
            "parents": [],
        }
        commit = Commit.model_validate(data)
        # Should show short SHA and first line of message
        assert "abc123d" in str(commit)
        assert "Initial commit" in str(commit)
