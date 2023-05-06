import requests
from datetime import datetime
import os
from git import Repo
import sys

# TODO:
# -------------------------------------
# - Exception-handling


# DESCRIPTION:
# -------------------------------------
# This script will retrieve the group-structure from the gitlab-server.
# It will then create a directory-structure (subgroups moved to roo - meaning currently no tree structure)
# to mimic the layout. It then clones all the projects found.
# Compression and cleanup is NOT handled by this script!


# LIMITATIONS & KNOWN ISSUES:
# -------------------------------------
# - Currently we use a single-level group structure. Groups can be nested but the backups are placed
#   in a single level. For now that's enough. Creating a tree-structure would just add unnecessary complexity

class Project:
    def __init__(self, project_id, name, ssh_url, web_url, description):
        self.project_id = project_id
        self.name = name
        self.ssh_url = ssh_url
        self.web_url = web_url
        self.description = description

    def get_project_id(self):
        return self.project_id

    def get_ssh_url(self):
        return self.ssh_url

    def get_name(self):
        return self.name


class Group:
    def __init__(self, group_id, parent_id, name, full_name, full_path, web_url, description):
        self.group_id = group_id
        self.parent_id = parent_id
        self.name = name
        self.full_name = full_name
        self.full_path = full_path
        self.web_url = web_url
        self.description = description
        self.groups = {}    # prepared for nested groups - but currently not used
        self.projects = {}

    def add_project(self, project_id, project):
        self.projects[project_id] = project

    def get_projects(self):
        return self.projects

    def get_group_id(self):
        return self.group_id

    def get_parent_id(self):
        return self.parent_id

    def get_name(self):
        return '%s_ID%s' % (self.name, self.group_id)


class Gitlab:
    def __init__(self):
        self.structure = {}

    # For now we ignore the fact that groups can be arranged in an n-deep tree structure.
    def add_group(self, group, parent_id=None):
        if parent_id is None:
            self.structure[group.get_group_id()] = group
        else:
            # TODO: This is where we instead would recurse if we need a nested structure.
            # For now we just pretend there is no parent_id provided (= mimic a flat structure)
            self.add_group(group, None)

    # Currently just a flat structure. Not taking future tree-structure into account
    def get_group_ids(self):
        return self.structure.keys()

    # In case of a tree-structure we have to search for the requested group. For now it's just a matter of picking it
    def get_group(self, group_id):
        return self.structure[group_id]


class Backup:
    def __init__(self, api_url, api_key, destination_dir):
        self.gitlab = Gitlab()
        self.datetime_str = str(datetime.now().strftime("%Y%m%d_%H%M%S"))
        self.backup_dir = os.path.join(destination_dir, self.datetime_str)
        self.api_key = api_key
        self.api_url = api_url

    @staticmethod
    def secure_filename(filename):
        return "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_', '-', ',')).rstrip('')

    def get_datetime_str(self):
        return self.datetime_str

    def get_backup_dir(self):
        return self.backup_dir

    def api_request(self, api_resource_str):
        url = '%s/%s' % (self.api_url, api_resource_str)  # TODO: Validation
        headers = {'Content-Type': 'application/json', 'PRIVATE-TOKEN': self.api_key}

        try:
            res = requests.get(url, headers=headers)
            if (res.status_code == 200):
                return res.json()
            else:
                exit("HTTP-error %s on request to %s" % (res.status_code, url))
        except Exception:
            exit("ERROR: Could not execute request to %s" % self.api_url)

    def build_structure(self):

        group_pages = []
        cur_groups = []
        page = 0

        while page == 0 or cur_groups:
            page = page + 1
            cur_groups = self.api_request('groups?per_page=20&page=' + str(page))

            if cur_groups:
                group_pages.append(cur_groups)

        # Traverse over groups
        for group_page in group_pages:
            for group in group_page:
                group = Group(
                    group['id'], group['parent_id'], group['name'], group['full_name'],
                    group['full_path'], group['web_url'], group['description']
                )

                # Append projects to group
                for project in self.api_request('groups/%s/projects' % group.get_group_id()):
                    project = Project(
                        project['id'], project['name'], project['ssh_url_to_repo'], project['web_url'], project['description']
                    )
                    group.add_project(project.get_project_id(), project)

                self.gitlab.add_group(group, group.get_parent_id())

    def create_backup_directory(self):
        os.makedirs(self.get_backup_dir())

    def clone_repositories(self):
        backup_directory = self.get_backup_dir()

        for group_id in self.gitlab.get_group_ids():
            group = self.gitlab.get_group(group_id)
            group_name = group.get_name()

            print("%s/" % group_name)

            # Create directory corresponding to group
            group_dir_path = os.path.join(backup_directory, self.secure_filename(group_name))
            os.makedirs(group_dir_path)

            # Traverse projects found in each group
            for project_id, project in group.get_projects().items():
                project_name = project.get_name()
                repo_path = os.path.join(group_dir_path, self.secure_filename(project_name))
                repo_ssh_url = project.get_ssh_url()
                try:
                    Repo.clone_from(repo_ssh_url, repo_path)
                    print("   --> cloning %s (%s)" % (project_name, repo_ssh_url))
                except Exception:
                    print("   --> ERROR: Failed to clone %s (%s)" % (project_name, repo_ssh_url))

    def execute(self):
        self.build_structure()
        self.create_backup_directory()
        self.clone_repositories()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Syntax:\n  gitlab_backup.py [API-URL] [API-KEY] [TARGET-DIR]\n")
        print("Example:\n  gitlab_backup.py \"https://gitlab.com/api/v4\" \"abcDEF123\" \"/home/foo/dest\"")
    else:
        if sys.argv[3] is None:
            destination_dir = os.getcwd()
        else:
            if os.path.isdir(sys.argv[3]):
                destination_dir = sys.argv[3]
            else:
                exit("Invalid destination directory")

        backup = Backup(sys.argv[1], sys.argv[2], destination_dir)
        backup.execute()
